import logging
import os
from datetime import datetime
from functools import reduce

import pandas as pd

from costreport import consts
from costreport.analysis.analyzers import DataAnalyzer
from costreport.app_config import AppConfig
from costreport.consts import OUTPUT_DIR, ItemType, ReportItemName
from costreport.cost_client import AwsCostClient
from costreport.data_container import DataContainer
from costreport.date_utils import get_today, get_months_back, get_days_back, get_first_day_next_month, \
    format_datetime, TIME_FORMAT
from costreport.model import ItemDefinition, DataSeries

logger = logging.getLogger(__name__)


class CostReporter:

    def __init__(self, exec_time: datetime, config: AppConfig, cost_client: AwsCostClient):
        self.exec_time = exec_time
        self.config = config
        self.cost_client = cost_client

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

        # TODO: execute data analyzer
        # self.exec_post_actions()

    def create_data_frame_from_results(self, cost_results):
        """
        returns list of identifiers and dict of values by key
        :param cost_results:
        :return:
        """
        columns = ['dates']
        data_set = {'dates': []}

        for i, v in enumerate(cost_results):
            start = v['TimePeriod']['Start']
            end = v['TimePeriod']['End']
            data_set['dates'].append(f'{start}_{end}')
            date_columns = ['dates']

            if v['Groups']:
                for g in v['Groups']:
                    key = g['Keys'][0]
                    # map account id to name:
                    if self.config.accounts and key in self.config.accounts:
                        key = self.config.accounts[key]

                    if not data_set.get(key):
                        # add new column to column list
                        columns.append(key)
                        # initialize array and pad with values if needed
                        data_set[key] = [] if i == 0 else [0] * i

                    date_columns.append(key)
                    data_set[key].append(float(g['Metrics']['UnblendedCost']['Amount']))

            # get columns in columns list that were not handled in this date and put '0'
            missing = [c for c in columns if c not in date_columns]
            for m in missing:
                data_set[m].append(0)

        return pd.DataFrame.from_dict(data_set)

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

    def generate_current_date(self):
        item_name = consts.ReportItemName.CURRENT_DATE.value
        exec_time_str = format_datetime(self.exec_time, TIME_FORMAT)
        self.item_defs.append(ItemDefinition(item_name,
                                             ItemType.VALUE,
                                             [exec_time_str]))

    def generate_monthly_report(self):
        item_name = consts.ReportItemName.MONTHLY_COST.value
        results = self.cost_client.request_cost_and_usage(
            start=get_months_back(self.config.periods.monthly_report_months_back),
            end=get_today(),
            request_name=item_name,
            group_by_dimensions=['LINKED_ACCOUNT'])

        dataframe = self.create_data_frame_from_results(results)
        self.data_container.add(item_name, dataframe)

        chart_def: ItemDefinition = self.create_item_definition(cost_results=results,
                                                                item_name=item_name,
                                                                chart_type=ItemType.STACK,
                                                                group="charts")

        # calculate months total and percentage
        def get_groups_total(groups):
            return round(reduce(lambda a, i: a + float(i['Metrics']['UnblendedCost']['Amount']), groups, 0))

        # month totals (all accounts)
        totals = {r['TimePeriod']['End']: get_groups_total(r['Groups']) for r in results}
        dataframe = pd.DataFrame.from_dict({
            'dates': totals.keys(),
            'values': totals.values()})
        self.data_container.add(ReportItemName.MONTHLY_TOTAL_COST.value, dataframe)

        self.item_defs.append(chart_def)

    def generate_daily_report(self):
        item_name = consts.ReportItemName.DAILY_COST.value

        results = self.cost_client.request_cost_and_usage(
            start=get_days_back(self.config.periods.daily_report_days_back),
            end=get_today(),
            request_name=item_name,
            group_by_dimensions=['LINKED_ACCOUNT'],
            granularity='DAILY')

        dataframe = self.create_data_frame_from_results(results)
        self.data_container.add(item_name, dataframe)

        item_def: ItemDefinition = self.create_item_definition(cost_results=results,
                                                               item_name=item_name,
                                                               chart_type=ItemType.BAR,
                                                               group="charts")
        self.item_defs.append(item_def)

        def get_groups_total(groups):
            return round(reduce(lambda a, i: a + float(i['Metrics']['UnblendedCost']['Amount']), groups, 0))

        # daily totals (all accounts)
        totals = {r['TimePeriod']['Start']: get_groups_total(r['Groups']) for r in results}
        dataframe = pd.DataFrame.from_dict({
            'dates': totals.keys(),
            'values': totals.values()})
        self.data_container.add(ReportItemName.DAILY_TOTAL_COST.value, dataframe)

        final_day = results[-2]
        final_day_date = final_day['TimePeriod']['Start']

        self.item_defs.append(ItemDefinition(ReportItemName.LAST_FINAL_DATE.value,
                                             ItemType.VALUE,
                                             [final_day_date]))

        for group in final_day['Groups']:
            cost = int(float(group['Metrics']['UnblendedCost']['Amount']))
            account_id = group["Keys"][0]
            account_name = account_id

            if self.config.accounts and self.config.accounts.get(account_id):
                account_name = self.config.accounts[account_id]

            self.item_defs.append(ItemDefinition(f'{account_name}',
                                                 ItemType.VALUE,
                                                 [f'${str(cost)}'],
                                                 group='Account Cost'))

    def generate_services_report(self):
        item_name = consts.ReportItemName.SERVICES_COST.value
        results = self.cost_client.request_cost_and_usage(
            start=get_days_back(self.config.periods.services_report_days_back),
            end=get_today(),
            request_name=item_name,
            granularity='DAILY',
            group_by_dimensions=['SERVICE'])

        dataframe = self.create_data_frame_from_results(results)
        self.data_container.add(item_name, dataframe)

        item_def: ItemDefinition = self.create_item_definition(cost_results=results,
                                                               item_name=item_name,
                                                               chart_type=ItemType.LINE,
                                                               filtered_keys=self.config.filtered_services,
                                                               group="charts")
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
        avail_tags = self.cost_client.get_available_tags(
            start_date=get_days_back(self.config.periods.tags_report_days_back),
            end_date=get_today())
        logger.info(f'available tags for tag reports time window:{avail_tags}')

    def generate_tag_reports(self):
        resource_tags = self.config.resource_tags
        if resource_tags:
            for tag in resource_tags:
                logger.info(f'generating cost report for tag {tag}')
                item_name = f"'{tag}' Resources Cost"
                results = self.cost_client.request_cost_and_usage(
                    start=get_days_back(self.config.periods.tags_report_days_back),
                    end=get_today(),
                    request_name=item_name,
                    granularity='DAILY',
                    group_by_tags=[tag])
                item_def: ItemDefinition = self.create_item_definition(cost_results=results,
                                                                       item_name=item_name,
                                                                       chart_type=ItemType.LINE,
                                                                       group="tags")
                self.item_defs.append(item_def)

    def generate_current_month_forecast(self):
        item_name = consts.ReportItemName.FORECAST.value
        forecast = self.cost_client.get_monthly_cost_forecast(get_today().isoformat(),
                                                              get_first_day_next_month().isoformat())

        dataframe = pd.DataFrame.from_dict({'values': [forecast]})
        self.data_container.add(item_name, dataframe)
        self.item_defs.append(ItemDefinition(item_name,
                                             ItemType.VALUE,
                                             [f'${str(forecast)}']))
