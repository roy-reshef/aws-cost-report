import logging
import os
from datetime import datetime

import pandas as pd

from costreport.analysis.analyzers import DataAnalyzer
from costreport.app_config import AppConfig
from costreport.collection.aws.cost_client import RawDateHandler
from costreport.collection.collector import Collector
from costreport.data_container import DataContainer
from costreport.model import ItemDefinition, DataSeries
from costreport.utils import consts
from costreport.utils.consts import OUTPUT_DIR, ItemType, ReportItemName
from costreport.utils.date_utils import format_datetime, TIME_FORMAT

logger = logging.getLogger(__name__)


class CostReporter:

    def __init__(self,
                 exec_time: datetime,
                 config: AppConfig,
                 collector: Collector):
        self.exec_time = exec_time
        self.config = config

        # TODO: this is temporary. use from consts
        CACHE_RESULTS_DIR = '.cache2'
        self.raw_data = RawDateHandler(config)
        self.collector = collector

        self.data_container: DataContainer = DataContainer()

        # report data dataframes definitions
        self.item_defs = []

        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)

    def generate(self):
        logger.info('fetching data and creating data dataframes')
        self.generate_current_date()
        self.generate_current_month_forecast()
        self.generate_daily_report()
        self.generate_monthly_report()
        self.generate_services_report()
        self.get_available_tags()
        self.generate_tag_reports()

        DataAnalyzer(self.data_container, self.item_defs).analyze()

    def create_item_definition(self,
                               cost_results,
                               item_name,
                               chart_type: ItemType,
                               filtered_keys=None,
                               group=None) -> ItemDefinition:

        if not filtered_keys:
            filtered_keys = []

        x_values = []
        data_series = {}
        for v in cost_results:
            start = v['TimePeriod']['Start']
            end = v['TimePeriod']['End']
            x_values.append(f'{start}_{end}')

            if v['Groups']:
                for i in v['Groups']:
                    key = i['Keys'][0]
                    if key not in filtered_keys:

                        # map account id to name:
                        if self.config.accounts and key in self.config.accounts:
                            key = self.config.accounts[key]

                        if not data_series.get(key):
                            data_series[key] = DataSeries(key, [])

                        series = data_series[key]

                        series.values.append(float(i['Metrics']['UnblendedCost']['Amount']))
            # TODO: support case when no groups are available
            # else:
            #     update({'Total': float(v['Total']['UnblendedCost']['Amount'])})

        return ItemDefinition(item_name,
                              chart_type,
                              x_values,
                              list(data_series.values()),
                              group=group)

    def create_item_definition_from_df(self,
                                       dataframe: pd.DataFrame,
                                       item_name,
                                       chart_type: ItemType,
                                       group=None,
                                       filtered_keys=None) -> ItemDefinition:
        if not filtered_keys:
            filtered_keys = []

        column_names = dataframe.columns.tolist()
        column_names = list(filter(lambda i: i == 'dates' or i not in filtered_keys, column_names))

        if 'dates' not in column_names:
            raise Exception("dataframe should have 'dates' column")

        x_values = dataframe['dates']
        column_names.remove('dates')
        data_series = []

        for names in column_names:
            data_values = dataframe[names].values

            # sanity check
            if len(data_values) != len(x_values):
                raise Exception('values array length does not match dates array length')

            series = DataSeries(names, data_values)
            data_series.append(series)

        return ItemDefinition(item_name,
                              chart_type,
                              x_values,
                              data_series,
                              group=group)

    def get_totals(self, dataframe):
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
        self.item_defs.append(ItemDefinition(item_name,
                                             ItemType.VALUE,
                                             [exec_time_str]))

    def generate_monthly_report(self):
        item_name = consts.ReportItemName.MONTHLY_COST.value
        dataframe = self.collector.get_monthly_report()
        self.data_container.add(item_name, dataframe)

        chart_def: ItemDefinition = self.create_item_definition_from_df(dataframe=dataframe,
                                                                        item_name=item_name,
                                                                        chart_type=ItemType.STACK,
                                                                        group="charts")

        # month totals (all accounts)
        self.data_container.add(ReportItemName.MONTHLY_TOTAL_COST.value, self.get_totals(dataframe))
        self.item_defs.append(chart_def)

    def generate_daily_report(self):
        item_name = consts.ReportItemName.DAILY_COST.value
        dataframe = self.collector.get_daily_report()
        self.data_container.add(item_name, dataframe)

        item_def: ItemDefinition = self.create_item_definition_from_df(dataframe=dataframe,
                                                                       item_name=item_name,
                                                                       chart_type=ItemType.BAR,
                                                                       group="charts")
        self.item_defs.append(item_def)

        account_col_names = dataframe.columns.tolist()
        account_col_names.remove('dates')

        self.data_container.add(ReportItemName.DAILY_TOTAL_COST.value, self.get_totals(dataframe))

        # generate final cost day date data item
        final_day = dataframe['dates'].tolist()[-2]

        self.item_defs.append(ItemDefinition(ReportItemName.LAST_FINAL_DATE.value,
                                             ItemType.VALUE,
                                             [final_day]))

        # final day cost for each account
        for account in account_col_names:
            cost = dataframe[account].tolist()[-2]

            self.item_defs.append(ItemDefinition(f'{account}',
                                                 ItemType.VALUE,
                                                 [f'${str(cost)}'],
                                                 group='Account Cost'))

    def generate_services_report(self):
        item_name = consts.ReportItemName.SERVICES_COST.value
        dataframe = self.collector.get_services_report()

        self.data_container.add(item_name, dataframe)

        item_def: ItemDefinition = self.create_item_definition_from_df(dataframe=dataframe,
                                                                       item_name=item_name,
                                                                       chart_type=ItemType.LINE,
                                                                       group="charts",
                                                                       filtered_keys=self.config.filtered_services)
        self.item_defs.append(item_def)

        # calculate services total cost
        service_names = dataframe.columns.values.tolist()
        service_names.remove('dates')

        total_values = {}
        # sum service cost
        for service_name in list(filter(lambda i: i not in self.config.filtered_services, service_names)):
            total_values[service_name] = round(dataframe[service_name].values.sum())

        # sort services by cost
        total_values = {k: v for k, v in sorted(total_values.items(), key=lambda item: item[1], reverse=True)}

        # top services (5 and others)
        top = {'others': 0}
        for i, k in enumerate(total_values):
            if i <= 5:
                top[k] = total_values[k]
            else:
                top['others'] = top['others'] + total_values[k]

        item_name = consts.ReportItemName.SERVICES_TOP_COST.value

        item_def: ItemDefinition = ItemDefinition(item_name,
                                                  item_type=ItemType.PIE,
                                                  x=list(top.keys()),
                                                  y=[DataSeries('values', list(top.values()))],
                                                  group="charts")
        self.item_defs.append(item_def)

    def get_available_tags(self):
        avail_tags = self.collector.get_available_tags()
        logger.info(f'available tags for tag reports time window:{avail_tags}')

    def generate_tag_reports(self):
        resource_tags = self.config.resource_tags
        if resource_tags:
            for tag in resource_tags:
                logger.info(f'generating cost report for tag {tag}')
                item_name = f"'{tag}' Resources Cost"
                dataframe = self.collector.get_tag_report(tag)
                item_def: ItemDefinition = self.create_item_definition_from_df(dataframe=dataframe,
                                                                               item_name=item_name,
                                                                               chart_type=ItemType.LINE,
                                                                               group="tags")
                self.item_defs.append(item_def)

    def generate_current_month_forecast(self):
        item_name = consts.ReportItemName.FORECAST.value
        dataframe = self.collector.get_current_month_forecast()
        forecast = dataframe['values'][0]
        self.data_container.add(item_name, dataframe)
        self.item_defs.append(ItemDefinition(item_name,
                                             ItemType.VALUE,
                                             [f'${str(forecast)}']))
