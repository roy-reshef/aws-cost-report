import logging
from abc import ABC, abstractmethod

from pandas import DataFrame

from costreport.data_container import DataContainer
from costreport.utils import data_utils
from costreport.utils.consts import ReportItemName

logger = logging.getLogger(__name__)


class DataAnalyzerBase(ABC):
    def __init__(self, data_container: DataContainer):
        self.data_container = data_container

    def analyze(self):
        logger.info(f'executing {self.__class__.__name__} data analyzer')
        self.analyze_internal()

    @abstractmethod
    def analyze_internal(self):
        raise NotImplementedError('must be implemented by subclasses')


class ForecastChangeAnalyzer(DataAnalyzerBase):
    def analyze_internal(self):
        month_totals: DataFrame = self.data_container.get(ReportItemName.MONTHLY_TOTAL_COST.value).value
        last_closed_month = month_totals['values'].values[-2]
        forecast = self.data_container.get(ReportItemName.FORECAST.value).value
        forecast_per = data_utils.calc_percentage(forecast, last_closed_month)
        self.data_container.add(ReportItemName.FORECAST_PER.value, forecast_per)


class MonthlyReportStats(DataAnalyzerBase):
    def analyze_internal(self):
        month_totals: DataFrame = self.data_container.get(ReportItemName.MONTHLY_TOTAL_COST.value).value
        values = month_totals['values'].values
        self.data_container.add(ReportItemName.MONTHLY_TOTAL_COST_MIN.value, round(values.min(), 1))
        self.data_container.add(ReportItemName.MONTHLY_TOTAL_COST_MAX.value, round(values.max(), 1))
        self.data_container.add(ReportItemName.MONTHLY_TOTAL_COST_MEAN.value, round(values.mean(), 1))
        self.data_container.add(ReportItemName.MONTHLY_TOTAL_COST_TOTAL.value, round(values.sum(), 1))


class DailyReportStats(DataAnalyzerBase):
    def analyze_internal(self):
        daily_totals: DataFrame = self.data_container.get(ReportItemName.DAILY_TOTAL_COST.value).value
        values = daily_totals['values'].values

        self.data_container.add(ReportItemName.DAILY_TOTAL_COST_MIN.value, round(values.min(), 1))
        self.data_container.add(ReportItemName.DAILY_TOTAL_COST_MAX.value, round(values.max(), 1))
        self.data_container.add(ReportItemName.DAILY_TOTAL_COST_MEAN.value, round(values.mean(), 1))
        self.data_container.add(ReportItemName.DAILY_TOTAL_COST_TOTAL.value, round(values.sum(), 1))


data_analyzers = [ForecastChangeAnalyzer, MonthlyReportStats, DailyReportStats]


class DataAnalyzer:
    def __init__(self, data_container: DataContainer):
        self.data_container = data_container

    def analyze(self):
        logger.info('executing data analyzers')
        for analyzer in data_analyzers:
            analyzer(self.data_container).analyze()
