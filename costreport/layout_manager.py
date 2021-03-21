import logging
import pathlib
from typing import List

import plotly.graph_objs as go
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from plotly.offline import plot

from costreport.cost_report_generator import ItemDefinition, ItemType

logger = logging.getLogger(__name__)

jinja_env = Environment(
    loader=FileSystemLoader(f'{pathlib.Path(__file__).parent.absolute()}/../report_templates'),
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

        template = jinja_env.get_template(self.config.template_name)
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
