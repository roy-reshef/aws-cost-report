from typing import Dict, Union

from pandas import DataFrame

from costreport.utils.consts import ReportItemGroup


class DataItem:
    def __init__(self, name, value, group: ReportItemGroup = None):
        self.name = name
        self.value = value
        self.group = group


class DataContainer:
    """
    holds results dataframes per ReportItemType
    """

    def __init__(self):
        self.data_items: Dict[str, DataItem] = {}

    def add(self, name: str, value: Union[DataFrame, str], group: ReportItemGroup = None):
        """
        :param name:
        :param value:
        :param group:
        :return:
        """
        self.data_items[name] = DataItem(name, value, group)

    def get(self, item_name: str) -> DataItem:
        return self.data_items[item_name]

    def get_value(self, item_name: str) -> Union[DataFrame, str]:
        return self.data_items[item_name].value

    def get_by_group(self, group: ReportItemGroup):
        return list(filter(lambda i: i.group == group, self.data_items.values()))
