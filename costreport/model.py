from typing import List

from costreport.utils.consts import ItemType


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
