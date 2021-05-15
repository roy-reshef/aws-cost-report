from typing import Dict

from pandas import DataFrame

from costreport.utils.consts import ReportItemName


class DataContainer:
    """
    holds results dataframes per ReportItemType
    """

    def __init__(self):
        self.dataframes: Dict = {}

    def add(self, item: ReportItemName, dataframe: DataFrame):
        self.dataframes[item] = dataframe

    def get(self, item_name) -> DataFrame:
        return self.dataframes[item_name]
