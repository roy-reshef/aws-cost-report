import json
import logging
import os
from datetime import datetime
from functools import reduce
from typing import List, Tuple, Dict

import plotly.graph_objs as go
from plotly.offline import plot

from costreport import consts, data_utils
from costreport.app_config import AppConfig
from costreport.consts import OUTPUT_DIR, ItemType, ReportItemName
from costreport.cost_client import AwsCostClient
from costreport.date_utils import get_today, get_months_back, get_days_back, get_first_day_next_month, \
    format_datetime, TIME_FORMAT
from costreport.intermediate_data import IntermediateData, IntermediateSimpleResult, IntermediateComplexResults

logger = logging.getLogger(__name__)


def _load_config():
    with open('../configuration.json', 'r') as c:
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


class CostReporter:

    def __init__(self, exec_time: datetime, config: AppConfig, cost_client: AwsCostClient):
        self.exec_time = exec_time
        self.config = config
        self.cost_client = cost_client

        self._intermediate_results: IntermediateData = IntermediateData()

        # report data items definitions
        self.item_defs = []

        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)

    def generate(self):
        logger.info('fetching data and creating data items')
        self.generate_current_date()
        self.generate_current_month_forecast()
        self.generate_daily_report()
        self.generate_monthly_report()
        self.generate_services_report()
        self.generate_tag_reports()

        self.exec_post_actions()

    def exec_post_actions(self):
        logger.info('executing post actions')
        month_totals: IntermediateComplexResults = self._intermediate_results.get(
            ReportItemName.MONTHLY_TOTAL_COST.value)
        last_closed_month = month_totals.values[-2]
        forecast = self._intermediate_results.get(ReportItemName.FORECAST.value).value
        forecast_per = data_utils.calc_percentage(forecast, last_closed_month)
        self.item_defs.append(ItemDefinition(ReportItemName.FORECAST_PER.value,
                                             ItemType.VALUE,
                                             [forecast_per]))

    def parse_result(self, cost_results) -> Tuple[List, Dict]:
        """
        returns list of identifiers and dict of values by key
        :param cost_results:
        :return:
        """
        x_values = []
        data_series = {}

        for v in cost_results:
            start = v['TimePeriod']['Start']
            end = v['TimePeriod']['End']
            x_values.append(f'{start}_{end}')

            if v['Groups']:
                for i in v['Groups']:
                    key = i['Keys'][0]
                    # map account id to name:
                    if self.config.accounts and key in self.config.accounts:
                        key = self.config.accounts[key]

                    if not data_series.get(key):
                        data_series[key] = DataSeries(key, [])

                    series = data_series[key]

                    series.values.append(float(i['Metrics']['UnblendedCost']['Amount']))

        return x_values, data_series

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
                        if self.config.accounts and key in self.config.accounts:
                            key = self.config.accounts[key]

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
        self._intermediate_results.add(item_name, IntermediateSimpleResult(exec_time_str))
        self.item_defs.append(ItemDefinition(item_name,
                                             ItemType.VALUE,
                                             [exec_time_str]))

    def generate_monthly_report(self):
        item_name = consts.ReportItemName.MONTHLY_COST.value
        results = self.cost_client.request_cost_and_usage(
            start=get_months_back(self.config.periods.monthly_report_months_back),
            end=get_today(),
            request_name=item_name,
            group_by_dimensions=['LINKED_ACCOUNT'])

        identifiers, values = self.parse_result(results)
        self._intermediate_results.add(item_name, IntermediateComplexResults(identifiers, values))

        chart_def: ItemDefinition = self.create_item_definition(cost_results=results,
                                                                item_name=item_name,
                                                                chart_type=ItemType.STACK,
                                                                group="charts")

        # calculate months total and percentage
        def get_groups_total(groups):
            return round(reduce(lambda a, i: a + float(i['Metrics']['UnblendedCost']['Amount']), groups, 0))

        totals = {r['TimePeriod']['End']: get_groups_total(r['Groups']) for r in results}
        self._intermediate_results.add(consts.ReportItemName.MONTHLY_TOTAL_COST.value,
                                       IntermediateComplexResults(list(totals.keys()),
                                                                  list(totals.values())))

        self.item_defs.append(chart_def)

    def generate_daily_report(self):
        item_name = consts.ReportItemName.DAILY_COST.value

        results = self.cost_client.request_cost_and_usage(
            start=get_days_back(self.config.periods.daily_report_days_back),
            end=get_today(),
            request_name=item_name,
            group_by_dimensions=['LINKED_ACCOUNT'],
            granularity='DAILY')

        identifiers, values = self.parse_result(results)
        self._intermediate_results.add(item_name, IntermediateComplexResults(identifiers, values))

        item_def: ItemDefinition = self.create_item_definition(cost_results=results,
                                                               item_name=item_name,
                                                               chart_type=ItemType.BAR,
                                                               group="charts")
        self.item_defs.append(item_def)
        final_day = results[-2]
        final_day_date = final_day['TimePeriod']['Start']
        for group in final_day['Groups']:
            cost = int(float(group['Metrics']['UnblendedCost']['Amount']))
            account_id = group["Keys"][0]
            account_name = account_id

            if self.config.accounts and self.config.accounts.get(account_id):
                account_name = self.config.accounts[account_id]

            self.item_defs.append(ItemDefinition(f'{account_name}({final_day_date})',
                                                 ItemType.VALUE,
                                                 [f'${str(cost)}'],
                                                 group='Account Cost'))

    def generate_services_report(self):
        item_name = consts.ReportItemName.SERVICES_COST.value
        results = self.cost_client.request_cost_and_usage(
            start=get_days_back(self.config.periods.services_report_days_back),
            end=get_today(),
            request_name=item_name,
            granularity='DAILY',
            group_by_dimensions=['SERVICE'])

        identifiers, values = self.parse_result(results)
        self._intermediate_results.add(item_name, IntermediateComplexResults(identifiers, values))

        item_def: ItemDefinition = self.create_item_definition(cost_results=results,
                                                               item_name=item_name,
                                                               chart_type=ItemType.LINE,
                                                               filtered_keys=self.config.filtered_services,
                                                               group="charts")
        self.item_defs.append(item_def)

    def generate_tag_reports(self):
        resource_tags = self.config.resource_tags
        if resource_tags:
            for tag in resource_tags:
                logger.info(f'generating cost report for tag {tag}')
                item_name = f"'{tag}' Resources Cost"
                results = self.cost_client.request_cost_and_usage(
                    start=get_days_back(self.config.periods.tags_report_days_back),
                    end=get_today(),
                    request_name=item_name,
                    granularity='DAILY',
                    group_by_tags=[tag])
                item_def: ItemDefinition = self.create_item_definition(cost_results=results,
                                                                       item_name=item_name,
                                                                       chart_type=ItemType.LINE,
                                                                       group="charts")
                self.item_defs.append(item_def)

    def generate_current_month_forecast(self):
        item_name = consts.ReportItemName.FORECAST.value
        forecast = self.cost_client.get_monthly_cost_forecast(get_today().isoformat(),
                                                              get_first_day_next_month().isoformat())
        self._intermediate_results.add(item_name, IntermediateSimpleResult(forecast))
        self.item_defs.append(ItemDefinition(item_name,
                                             ItemType.VALUE,
                                             [f'${str(forecast)}']))

    def post_processing(self):
        """
        generate additional data items based on existing data items.
        :return:
        """
        ...
