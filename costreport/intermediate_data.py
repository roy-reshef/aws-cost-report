from typing import Dict

from costreport.consts import ReportItemName


class IntermediateResults:
    pass


class IntermediateSimpleResult(IntermediateResults):
    def __init__(self, value):
        self.value = value


class IntermediateComplexResults(IntermediateResults):
    def __init__(self, identifiers, values):
        self.identifiers = identifiers
        self.values = values


class IntermediateData:
    """
    holds intermediate_results per ReportItemType
    """

    def __init__(self):
        self.items: Dict = {}

    def add(self, item: ReportItemName, intermediate_results: IntermediateResults):
        self.items[item] = intermediate_results

    def get(self, item_name):
        return self.items[item_name]
