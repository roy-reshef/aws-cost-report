import json
import logging
import os
from datetime import datetime
from enum import unique, Enum
from functools import reduce
from typing import List

import plotly.graph_objs as go
from jinja2 import Environment, select_autoescape, FileSystemLoader
from markupsafe import Markup
from plotly.offline import plot

from costreport import consts
from costreport.consts import OUTPUT_DIR, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, REGION_NAME
from costreport.cost_client import AwsCostClient
from costreport.date_utils import get_today, get_months_back, get_days_back, get_first_day_next_month, get_time, \
    format_datetime, TIME_FORMAT
from costreport.intermediate_data import IntermediateData
from costreport.output_manager import OutputManager

jinja_env = Environment(
    loader=FileSystemLoader(f'{os.getcwd()}/report_templates'),
    autoescape=select_autoescape(['html'])
)

logger = logging.getLogger(__name__)
logger.setLevel(consts.LOGGING_LEVEL)
log_handler = logging.StreamHandler()
logger.addHandler(log_handler)


@unique
class ItemType(Enum):
    BAR = 'bar'
    LINE = 'line'
    STACK = 'stack'
    VALUE = 'value'


def _load_config():
    with open('configuration.json', 'r') as c:
        configuration = c.read()

    return json.loads(configuration)


class DataSeries:
    def __init__(self, name, values: List[int]):
        self.name = name
        self.values = values


class ItemDefinition:
    def __init__(self, item_name, item_type: ItemType, x: List[str], y: List[DataSeries] = None, group=None):
        self.item_name = item_name
        self.chart_type = item_type
        self.x = x
        self.y = y
        self.group = group


class ChartPlotter:

    @staticmethod
    def _get_value_div(chart_def: ItemDefinition) -> str:
        return chart_def.x[0]

    @staticmethod
    def _get_chart_div(chart_def: ItemDefinition) -> str:
        data = []
        x = chart_def.x
        y = chart_def.y

        for series in y:
            if chart_def.chart_type == ItemType.BAR or chart_def.chart_type == ItemType.STACK:
                data.append(go.Bar(name=series.name, x=x, y=series.values))
            elif chart_def.chart_type == ItemType.LINE:
                data.append(go.Line(name=series.name, x=x, y=series.values))
            else:
                raise Exception(f'unsupported chart type {chart_def.chart_type}')

        fig = go.Figure(data=data)

        # TODO: configurable
        fig.update_layout(template="plotly_dark")

        if chart_def.chart_type == ItemType.STACK:
            fig.update_layout(barmode='stack')

        return plot(fig, output_type='div')

    def get_div(self, chart_def: ItemDefinition) -> str:
        if chart_def.chart_type == ItemType.BAR or \
                chart_def.chart_type == ItemType.LINE or \
                chart_def.chart_type == ItemType.STACK:
            div = self._get_chart_div(chart_def)
        elif chart_def.chart_type == ItemType.VALUE:
            div = self._get_value_div(chart_def)
        else:
            raise Exception(f'unsupported chart type {chart_def.chart_type}')

        return div


class LayoutManager(object):

    def __init__(self, items_defs: List[ItemDefinition], config):
        self.items_defs = items_defs
        self.plotter: ChartPlotter = ChartPlotter()

    def layout(self, data_items=None) -> str:
        """
        returns html string
        :return:
        """

        if not data_items:
            data_items = {}

        template = jinja_env.get_template(config.get('template_name', 'default.html'))
        logger.info(f'using {template} template file')

        for item_def in self.items_defs:
            div = self.plotter.get_div(item_def)

            if item_def.chart_type != ItemType.VALUE:
                div = Markup(div)

            if item_def.group is None:
                data_items[item_def.item_name] = div
            else:
                if data_items.get(item_def.group) is None:
                    data_items[item_def.group] = {}

                data_items[item_def.group][item_def.item_name] = div

        return template.render(items=data_items)


class CostReporter:

    def __init__(self, exec_time: datetime, config, cost_client: AwsCostClient):
        self.exec_time = exec_time
        self.config = config
        self.cost_client = cost_client

        self._intermediate_results: IntermediateData = IntermediateData()

        # report data items definitions
        self.item_defs = []

        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)

    def generate(self):
        self.generate_current_date()
        self.generate_current_month_forecast()
        self.generate_last_stable_accounts_cost_report()
        self.generate_daily_report()
        self.generate_monthly_report()
        self.generate_services_report()
        self.generate_tag_reports()

    def create_item_definition(self,
                               cost_results,
                               item_name,
                               chart_type: ItemType,
                               filtered_keys=None,
                               group=None) -> ItemDefinition:

        if not filtered_keys:
            filtered_keys = []

        x_values = []
        data_series = {}
        for v in cost_results:
            start = v['TimePeriod']['Start']
            end = v['TimePeriod']['End']
            x_values.append(f'{start}_{end}')

            if v['Groups']:
                for i in v['Groups']:
                    key = i['Keys'][0]
                    if key not in filtered_keys:

                        # map account id to name:
                        if self.config.get('accounts') and key in self.config['accounts']:
                            key = self.config['accounts'][key]

                        if not data_series.get(key):
                            data_series[key] = DataSeries(key, [])

                        series = data_series[key]

                        series.values.append(float(i['Metrics']['UnblendedCost']['Amount']))
            # TODO: support case when no groups are available
            # else:
            #     update({'Total': float(v['Total']['UnblendedCost']['Amount'])})

        return ItemDefinition(item_name,
                              chart_type,
                              x_values,
                              list(data_series.values()),
                              group=group)

    def generate_current_date(self):
        item_name = consts.ReportItemName.CURRENT_DATE.value
        exec_time_str = format_datetime(self.exec_time, TIME_FORMAT)
        self._intermediate_results.add(item_name, [exec_time_str])
        self.item_defs.append(ItemDefinition(item_name,
                                             ItemType.VALUE,
                                             [exec_time_str]))

    def generate_monthly_report(self):
        item_name = consts.ReportItemName.MONTHLY_COST.value
        results = self.cost_client.request_cost_and_usage(start=get_months_back(self.config['periods']
                                                                                ['monthly_report_months_back']),
                                                          end=get_today(),
                                                          request_name=item_name,
                                                          group_by_dimensions=['LINKED_ACCOUNT'])

        self._intermediate_results.add(item_name, results)

        chart_def: ItemDefinition = self.create_item_definition(cost_results=results,
                                                                item_name=item_name,
                                                                chart_type=ItemType.STACK,
                                                                group="charts")

        # calculate months total and percentage
        def get_groups_total(groups):
            return round(reduce(lambda a, i: a + float(i['Metrics']['UnblendedCost']['Amount']), groups, 0))

        totals = {r['TimePeriod']['End']: get_groups_total(r['Groups']) for r in results}
        # TODO: generate text item...

        self.item_defs.append(chart_def)

    def generate_daily_report(self):
        item_name = consts.ReportItemName.DAILY_COST.value
        results = self.cost_client.request_cost_and_usage(start=get_days_back(self.config['periods']
                                                                              ['daily_report_days_back']),
                                                          end=get_today(),
                                                          request_name=item_name,
                                                          group_by_dimensions=['LINKED_ACCOUNT'],
                                                          granularity='DAILY')

        self._intermediate_results.add(item_name, results)

        item_def: ItemDefinition = self.create_item_definition(cost_results=results,
                                                               item_name=item_name,
                                                               chart_type=ItemType.BAR,
                                                               group="charts")
        item_def.generate_standalone_report = True
        self.item_defs.append(item_def)

    def generate_services_report(self):
        item_name = consts.ReportItemName.SERVICES_COST.value
        results = self.cost_client.request_cost_and_usage(start=get_days_back(self.config['periods']
                                                                              ['services_report_days_back']),
                                                          end=get_today(),
                                                          request_name=item_name,
                                                          granularity='DAILY',
                                                          group_by_dimensions=['SERVICE'])

        self._intermediate_results.add(item_name, results)

        item_def: ItemDefinition = self.create_item_definition(cost_results=results,
                                                               item_name=item_name,
                                                               chart_type=ItemType.LINE,
                                                               filtered_keys=self.config['filtered_services'],
                                                               group="charts")
        item_def.generate_standalone_report = True
        self.item_defs.append(item_def)

    def generate_tag_reports(self):
        resource_tags = self.config.get('resource_tags')
        if resource_tags:
            for tag in resource_tags:
                logger.info(f'generating cost report for tag {tag}')
                item_name = f"'{tag}' Resources Cost"
                results = self.cost_client.request_cost_and_usage(start=get_days_back(self.config['periods']
                                                                                      ['tags_report_days_back']),
                                                                  end=get_today(),
                                                                  request_name=item_name,
                                                                  granularity='DAILY',
                                                                  group_by_tags=[tag])
                item_def: ItemDefinition = self.create_item_definition(cost_results=results,
                                                                       item_name=item_name,
                                                                       chart_type=ItemType.LINE,
                                                                       group="charts")
                item_def.generate_standalone_report = True
                self.item_defs.append(item_def)

    def generate_last_stable_accounts_cost_report(self):
        item_name = consts.ReportItemName.ACCOUNTS_COST.value
        results = self.cost_client.request_cost_and_usage(start=get_days_back(2),
                                                          end=get_days_back(1),
                                                          request_name=item_name,
                                                          group_by_dimensions=['LINKED_ACCOUNT'])

        self._intermediate_results.add(item_name, results)

        for group in results[0]['Groups']:
            cost = int(float(group['Metrics']['UnblendedCost']['Amount']))
            account_id = group["Keys"][0]
            account_name = account_id

            if self.config.get('accounts') and self.config["accounts"].get(account_id):
                account_name = self.config["accounts"][account_id]

            item_name = f'Latest Stable Total Cost {account_name}'

            self.item_defs.append(ItemDefinition(item_name,
                                                 ItemType.VALUE,
                                                 [f'${str(cost)}'],
                                                 group='Account Cost'))

    def generate_current_month_forecast(self):
        item_name = consts.ReportItemName.FORECAST.value
        forecast = self.cost_client.get_monthly_cost_forecast(get_today().isoformat(),
                                                              get_first_day_next_month().isoformat())
        self._intermediate_results.add(item_name, [forecast])
        self.item_defs.append(ItemDefinition(item_name,
                                             ItemType.VALUE,
                                             [f'${str(forecast)}']))

    def post_processing(self):
        """
        generate additional data items based on existing data items.
        :return: 
        """


def validate_env_variables():
    """
    returns boolean value indicating validity of configuration
    :return:
    """
    valid = True

    if not AWS_ACCESS_KEY_ID:
        logger.error('AWS_ACCESS_KEY_ID environment variable is required for execution')
        valid = False

    if not AWS_SECRET_ACCESS_KEY:
        logger.error('AWS_SECRET_ACCESS_KEY environment variable is required for execution')
        valid = False

    if not REGION_NAME:
        logger.error('REGION_NAME environment variable is required for operation')
        valid = False

    return valid


if __name__ == '__main__':
    if not validate_env_variables():
        exit(1)

    exec_time = get_time()
    config = _load_config()
    reporter = CostReporter(exec_time, config, AwsCostClient(config))
    reporter.generate()

    data_items = {'Report Title': config["report_title"]}
    report_html_str = LayoutManager(reporter.item_defs, config).layout(data_items)

    output_manager = OutputManager(exec_time, config)
    output_manager.output(report_html_str)
