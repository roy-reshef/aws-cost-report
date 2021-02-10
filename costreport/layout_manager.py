import logging
import pathlib
from typing import List

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from costreport.cost_report_generator import ItemDefinition, ChartPlotter, ItemType

logger = logging.getLogger(__name__)

jinja_env = Environment(
    loader=FileSystemLoader(f'{pathlib.Path(__file__).parent.absolute()}/../report_templates'),
    autoescape=select_autoescape(['html'])
)


class LayoutManager(object):

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

        return template.render(items=data_items)
