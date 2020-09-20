from typing import Dict

from costreport.consts import ReportItemName


class IntermediateData:
    """
    holds intermediate data per ReportItemType
    """

    def __init__(self):
        self.item_defs: Dict = {}

    def add(self, item: ReportItemName, values: list):
        self.item_defs[item] = values
