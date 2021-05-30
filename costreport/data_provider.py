import logging
from datetime import datetime

import pandas as pd

from costreport.app_config import AppConfig
from costreport.collection.collector import Collector
from costreport.data_container import DataContainer
from costreport.utils import consts
from costreport.utils.consts import ReportItemName, ReportItemGroup
from costreport.utils.date_utils import format_datetime, TIME_FORMAT

logger = logging.getLogger(__name__)


class DataProvider:

    def __init__(self,
                 exec_time: datetime,
                 config: AppConfig,
                 collector: Collector):
        self.exec_time = exec_time
        self.config = config
        self.collector = collector

        self.data_container: DataContainer = DataContainer()

    def generate(self) -> DataContainer:
        logger.info('fetching data and creating data items')
        self.generate_current_date()
        self.generate_current_month_forecast()
        self.generate_daily_report()
        self.generate_monthly_report()
        self.generate_services_report()
        self.get_available_tags()
        self.generate_tag_reports()

        return self.data_container

    def get_available_tags(self):
        avail_tags = self.collector.get_available_tags()
        logger.info(f'available tags for tag reports time window:{avail_tags}')

    @staticmethod
    def get_totals(dataframe):
        account_col_names = dataframe.columns.tolist()
        account_col_names.remove('dates')

        totals = []
        for i in range(0, len(dataframe['dates'].tolist())):
            total = 0
            for account in account_col_names:
                total += dataframe[account].tolist()[i]
            totals.append(total)

        return pd.DataFrame.from_dict({
            'dates': dataframe['dates'].tolist(),
            'values': totals})

    def generate_current_date(self):
        item_name = consts.ReportItemName.CURRENT_DATE.value
        exec_time_str = format_datetime(self.exec_time, TIME_FORMAT)
        self.data_container.add(item_name, exec_time_str)

    def generate_monthly_report(self):
        item_name = consts.ReportItemName.MONTHLY_COST.value
        dataframe = self.collector.get_monthly_report()
        self.data_container.add(item_name, dataframe)
        # month totals (all accounts)
        self.data_container.add(ReportItemName.MONTHLY_TOTAL_COST.value, self.get_totals(dataframe))

    def generate_daily_report(self):
        item_name = consts.ReportItemName.DAILY_COST.value
        dataframe = self.collector.get_daily_report()
        self.data_container.add(item_name, dataframe)

        self.data_container.add(ReportItemName.DAILY_TOTAL_COST.value, self.get_totals(dataframe))

    def generate_services_report(self):
        item_name = consts.ReportItemName.SERVICES_COST.value
        dataframe = self.collector.get_services_report()

        self.data_container.add(item_name, dataframe)

    def generate_tag_reports(self):
        resource_tags = self.config.resource_tags
        if resource_tags:
            for tag in resource_tags:
                logger.info(f'generating cost report for tag {tag}')
                item_name = f"'{tag}' Resources Cost"
                dataframe = self.collector.get_tag_report(tag)
                self.data_container.add(item_name, dataframe, ReportItemGroup.TAGS)

    def generate_current_month_forecast(self):
        item_name = consts.ReportItemName.FORECAST.value
        dataframe = self.collector.get_current_month_forecast()
        forecast = dataframe['values'][0]
        self.data_container.add(item_name, forecast)
