import logging
import pathlib
from typing import List

import pandas as pd
import plotly.graph_objs as go
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from plotly.offline import plot

from costreport.data_container import DataContainer
from costreport.model import DataSeries, ItemDefinition
from costreport.report_generators.generator_base import ReportGeneratorBase
from costreport.utils.consts import ReportItemName, ItemType, ReportItemGroup

logger = logging.getLogger(__name__)

jinja_env = Environment(
    loader=FileSystemLoader(f'{pathlib.Path(__file__).parent.absolute()}/../../report_templates'),
    autoescape=select_autoescape(['html'])
)


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
            if chart_def.chart_type in [ItemType.BAR, ItemType.STACK]:
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

    @staticmethod
    def _get_pie_chart_div(chart_def: ItemDefinition) -> str:
        labels = chart_def.x
        values = chart_def.y[0].values

        fig = go.Figure(data=[go.Pie(labels=labels, values=values, textinfo='label+percent',
                                     insidetextorientation='radial')])

        fig.update_layout(template="plotly_dark")
        return plot(fig, output_type='div')

    def get_div(self, chart_def: ItemDefinition) -> str:
        if chart_def.chart_type in [ItemType.BAR, ItemType.LINE, ItemType.STACK]:
            div = self._get_chart_div(chart_def)
        elif chart_def.chart_type == ItemType.PIE:
            div = self._get_pie_chart_div(chart_def)
        elif chart_def.chart_type == ItemType.VALUE:
            div = self._get_value_div(chart_def)
        else:
            raise Exception(f'unsupported chart type {chart_def.chart_type}')

        return div


class LayoutManager:

    def __init__(self, items_defs: List[ItemDefinition], config):
        self.items_defs = items_defs
        self.plotter: ChartPlotter = ChartPlotter()
        self.config = config

    def layout(self, data_items=None) -> str:
        """
        returns html string
        :return:
        """

        if not data_items:
            data_items = {}

        template = jinja_env.get_template(self.config['template_name'])
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

        # in case there are no tags entries
        if not data_items.get("tags", None):
            data_items['tags'] = {}

        return template.render(items=data_items)


class HTMLReportGenerator(ReportGeneratorBase):

    def __init__(self, data_container: DataContainer, config, filtered_services):
        super().__init__(data_container, config, filtered_services)

    def generate(self, additional_data_items):
        items_def = self._data_to_items_defs()
        return LayoutManager(items_def, self.config).layout(additional_data_items)

    def create_item_definition_from_df(self,
                                       dataframe: pd.DataFrame,
                                       item_name,
                                       chart_type: ItemType,
                                       group=None,
                                       filtered_keys=None) -> ItemDefinition:
        if not filtered_keys:
            filtered_keys = []

        column_names = dataframe.columns.tolist()
        column_names = list(filter(lambda i: i == 'dates' or i not in filtered_keys, column_names))

        if 'dates' not in column_names:
            raise Exception("dataframe should have 'dates' column")

        x_values = dataframe['dates']
        column_names.remove('dates')
        data_series = []

        for names in column_names:
            data_values = dataframe[names].values

            # sanity check
            if len(data_values) != len(x_values):
                raise Exception('values array length does not match dates array length')

            series = DataSeries(names, data_values)
            data_series.append(series)

        return ItemDefinition(item_name,
                              chart_type,
                              x_values,
                              data_series,
                              group=group)

    def _data_to_items_defs(self):
        items_defs = []

        def __add_value(name: ReportItemName):
            val = self.data_container.get_value(name.value)
            items_defs.append(ItemDefinition(name.value,
                                             ItemType.VALUE,
                                             [val]))

        for item in [ReportItemName.CURRENT_DATE,
                     ReportItemName.FORECAST_PER,
                     ReportItemName.MONTHLY_TOTAL_COST_MIN,
                     ReportItemName.MONTHLY_TOTAL_COST_MAX,
                     ReportItemName.MONTHLY_TOTAL_COST_MEAN,
                     ReportItemName.MONTHLY_TOTAL_COST_TOTAL,
                     ReportItemName.DAILY_TOTAL_COST_MIN,
                     ReportItemName.DAILY_TOTAL_COST_MAX,
                     ReportItemName.DAILY_TOTAL_COST_MEAN,
                     ReportItemName.DAILY_TOTAL_COST_TOTAL
                     ]:
            __add_value(item)

        item_name = ReportItemName.FORECAST.value
        forecast = self.data_container.get_value(item_name)
        items_defs.append(ItemDefinition(item_name,
                                         ItemType.VALUE,
                                         [f'${str(forecast)}']))

        item_name = ReportItemName.MONTHLY_COST.value
        monthly_cost_df = self.data_container.get_value(item_name)
        items_defs.append(self.create_item_definition_from_df(dataframe=monthly_cost_df,
                                                              item_name=item_name,
                                                              chart_type=ItemType.STACK,
                                                              group=ReportItemGroup.CHARTS.value))

        item_name = ReportItemName.DAILY_COST.value
        daily_cost_df = self.data_container.get_value(item_name)
        items_defs.append(self.create_item_definition_from_df(dataframe=daily_cost_df,
                                                              item_name=item_name,
                                                              chart_type=ItemType.BAR,
                                                              group=ReportItemGroup.CHARTS.value))

        # generate final cost day date data item
        final_day = daily_cost_df['dates'].tolist()[-2]

        items_defs.append(ItemDefinition(ReportItemName.LAST_FINAL_DATE.value,
                                         ItemType.VALUE,
                                         [final_day]))

        # final day cost for each account
        account_col_names = daily_cost_df.columns.tolist()
        account_col_names.remove('dates')

        for account in account_col_names:
            cost = daily_cost_df[account].tolist()[-2]

            items_defs.append(ItemDefinition(f'{account}',
                                             ItemType.VALUE,
                                             [f'${str(cost)}'],
                                             group=ReportItemGroup.ACCOUNT_COST.value))

        # services cost
        item_name = ReportItemName.SERVICES_COST.value
        services_cost_df = self.data_container.get_value(item_name)
        item_def: ItemDefinition = self.create_item_definition_from_df(dataframe=services_cost_df,
                                                                       item_name=item_name,
                                                                       chart_type=ItemType.LINE,
                                                                       group=ReportItemGroup.CHARTS.value,
                                                                       filtered_keys=self.filtered_services)
        items_defs.append(item_def)

        # calculate services total cost
        service_names = services_cost_df.columns.values.tolist()
        service_names.remove('dates')

        total_values = {}
        # sum service cost
        for service_name in list(filter(lambda i: i not in self.filtered_services, service_names)):
            total_values[service_name] = round(services_cost_df[service_name].values.sum())

        # sort services by cost
        total_values = {k: v for k, v in sorted(total_values.items(), key=lambda item: item[1], reverse=True)}

        # top services (5 and others)
        top = {'others': 0}
        for i, k in enumerate(total_values):
            if i <= 5:
                top[k] = total_values[k]
            else:
                top['others'] = top['others'] + total_values[k]

        item_name = ReportItemName.SERVICES_TOP_COST.value
        item_def: ItemDefinition = ItemDefinition(item_name,
                                                  item_type=ItemType.PIE,
                                                  x=list(top.keys()),
                                                  y=[DataSeries('values', list(top.values()))],
                                                  group=ReportItemGroup.CHARTS.value)
        items_defs.append(item_def)

        # tags cost
        tag_items = self.data_container.get_by_group(ReportItemGroup.TAGS)
        for tag_item in tag_items:
            item_def: ItemDefinition = self.create_item_definition_from_df(dataframe=tag_item.value,
                                                                           item_name=tag_item.name,
                                                                           chart_type=ItemType.LINE,
                                                                           group=ReportItemGroup.TAGS.value)
            items_defs.append(item_def)

        return items_defs
