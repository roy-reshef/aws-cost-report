import logging
from abc import ABC, abstractmethod
from typing import List

from pandas import DataFrame

from costreport import data_utils
from costreport.consts import ReportItemName, ItemType
from costreport.data_container import DataContainer
from costreport.model import ItemDefinition

logger = logging.getLogger(__name__)


class DataAnalyzerBase(ABC):
    def __init__(self, data_container: DataContainer, item_defs: List[ItemDefinition]):
        self.data_container = data_container
        self.item_defs = item_defs

    def analyze(self):
        logger.info(f'executing {self.__class__.__name__} data analyzer')
        self.analyze_internal()

    @abstractmethod
    def analyze_internal(self):
        raise NotImplementedError(f'must be implemented by subclasses')


class ForecastChangeAnalyzer(DataAnalyzerBase):
    def analyze_internal(self):
        month_totals: DataFrame = self.data_container.get(ReportItemName.MONTHLY_TOTAL_COST.value)
        last_closed_month = month_totals['values'].values[-2]
        forecast = self.data_container.get(ReportItemName.FORECAST.value)
        forecast_per = data_utils.calc_percentage(forecast['values'].values[0], last_closed_month)
        self.item_defs.append(ItemDefinition(ReportItemName.FORECAST_PER.value,
                                             ItemType.VALUE,
                                             [forecast_per]))


class MonthlyReportStats(DataAnalyzerBase):
    def analyze_internal(self):
        month_totals: DataFrame = self.data_container.get(ReportItemName.MONTHLY_TOTAL_COST.value)
        values = month_totals['values'].values

        self.item_defs.append(ItemDefinition(ReportItemName.MONTHLY_TOTAL_COST_MIN.value,
                                             ItemType.VALUE,
                                             [values.min()]))

        self.item_defs.append(ItemDefinition(ReportItemName.MONTHLY_TOTAL_COST_MAX.value,
                                             ItemType.VALUE,
                                             [values.max()]))

        self.item_defs.append(ItemDefinition(ReportItemName.MONTHLY_TOTAL_COST_MEAN.value,
                                             ItemType.VALUE,
                                             [values.mean()]))

        self.item_defs.append(ItemDefinition(ReportItemName.MONTHLY_TOTAL_COST_TOTAL.value,
                                             ItemType.VALUE,
                                             [values.sum()]))


class DailyReportStats(DataAnalyzerBase):
    def analyze_internal(self):
        daily_totals: DataFrame = self.data_container.get(ReportItemName.DAILY_TOTAL_COST.value)
        values = daily_totals['values'].values

        self.item_defs.append(ItemDefinition(ReportItemName.DAILY_TOTAL_COST_MIN.value,
                                             ItemType.VALUE,
                                             [values.min()]))

        self.item_defs.append(ItemDefinition(ReportItemName.DAILY_TOTAL_COST_MAX.value,
                                             ItemType.VALUE,
                                             [values.max()]))

        self.item_defs.append(ItemDefinition(ReportItemName.DAILY_TOTAL_COST_MEAN.value,
                                             ItemType.VALUE,
                                             [values.mean()]))

        self.item_defs.append(ItemDefinition(ReportItemName.DAILY_TOTAL_COST_TOTAL.value,
                                             ItemType.VALUE,
                                             [values.sum()]))
        
        
data_analyzers = [ForecastChangeAnalyzer, MonthlyReportStats, DailyReportStats]


class DataAnalyzer:
    def __init__(self, data_container: DataContainer, item_defs: List[ItemDefinition]):
        self.data_container = data_container
        self.item_defs = item_defs

    def analyze(self):
        logger.info('executing data analyzers')
        for analyzer in data_analyzers:
            analyzer(self.data_container, self.item_defs).analyze()
