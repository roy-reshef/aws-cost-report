import json
import logging
import os
import subprocess
from datetime import date

import boto3

from costreport.app_config import AppConfig
from costreport.utils.cache_manager import RawDateCacheManager
from costreport.utils.consts import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, REGION_NAME, OUTPUT_DIR

logger = logging.getLogger(__name__)


class AwsCostClient:

    def __init__(self, config: AppConfig, cache: RawDateCacheManager):
        self.config = config
        self.cache = cache
        self.client = boto3.client('ce',
                                   aws_access_key_id=AWS_ACCESS_KEY_ID,
                                   aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                                   region_name=REGION_NAME)

    def load_previous_result(self, key):
        previous_result = None
        if self.cache.enabled:
            raw_result = self.cache.get(key)
            if raw_result:
                previous_result = json.loads(raw_result)

        return previous_result

    @staticmethod
    def get_enriched_env():
        p_env = os.environ.copy()
        p_env['AWS_ACCESS_KEY_ID'] = AWS_ACCESS_KEY_ID
        p_env['AWS_SECRET_ACCESS_KEY'] = AWS_SECRET_ACCESS_KEY
        p_env['AWS_DEFAULT_REGION'] = REGION_NAME

        return p_env

    def get_monthly_cost_forecast(self, start_date, end_date):
        res_data = self.load_previous_result('monthly_forecast')

        if not res_data:
            logger.info("getting cost forecast from AWS")

            if self.config.filtered_costs:
                costs_filter = {"Not": {"Dimensions": {"Key": "RECORD_TYPE", "Values": self.config.filtered_costs}}}
                cost_filter_file = f'{OUTPUT_DIR}/cost_filter.json'

                with open(cost_filter_file, 'w') as f:
                    json.dump(costs_filter, f)

            p_env = self.get_enriched_env()

            params = ['aws', 'ce', 'get-cost-forecast',
                      '--metric', 'UNBLENDED_COST',
                      '--time-period', f'Start={start_date},End={end_date}',
                      '--granularity=MONTHLY']

            if self.config.filtered_costs:
                params.extend(['--filter', f'file://{cost_filter_file}'])

            result = subprocess.Popen(params,
                                      env=p_env,
                                      stdout=subprocess.PIPE).communicate()[0]
            self.cache.save('monthly_forecast', result.decode("utf-8"))
            res_data = json.loads(result)

            if self.config.filtered_costs:
                os.remove(cost_filter_file)

        return int(float(res_data['Total']['Amount']))

    def get_available_tags(self, start_date, end_date):
        res_data = self.load_previous_result('available_tags')

        if not res_data:
            logger.info("getting available tags from AWS")

            p_env = self.get_enriched_env()

            params = ['aws', 'ce', 'get-tags', '--time-period', f'Start={start_date},End={end_date}']

            result = subprocess.Popen(params,
                                      env=p_env,
                                      stdout=subprocess.PIPE).communicate()[0]
            self.cache.save('available_tags', result.decode("utf-8"))
            res_data = json.loads(result)

        return res_data['Tags']

    def request_cost_and_usage(self,
                               start: date,
                               end: date,
                               request_name: str,
                               granularity='MONTHLY',
                               group_by_dimensions=None,
                               group_by_tags=None):
        """

        :param start:
        :param end:
        :param request_name: _intermediate_results data set name
        :param granularity: DAILY or MONTHLY
        :param group_by_dimensions: list of dimensions to group by
        :param group_by_tags: list of tags to group by
        :return:
        """
        request_name = request_name.lower().replace(' ', '_')
        results = self.load_previous_result(request_name)

        if not results:
            logger.info(f'getting {request_name} data from AWS')
            groups = []

            if group_by_dimensions:
                groups = list(map(lambda d: {"Type": "DIMENSION", "Key": d}, group_by_dimensions))

            if group_by_tags:
                groups.extend(list(map(lambda d: {"Type": "TAG", "Key": d}, group_by_tags)))

            results = []

            token = None
            while True:
                if token:
                    kwargs = {'NextPageToken': token}
                else:
                    kwargs = {}

                if self.config.filtered_costs:
                    data = self.client.get_cost_and_usage(
                        TimePeriod={
                            'Start': start.isoformat(),
                            'End': end.isoformat()
                        },
                        Granularity=granularity,
                        Metrics=[
                            'UnblendedCost',
                        ],
                        GroupBy=groups,
                        Filter={
                            "Not": {
                                "Dimensions": {
                                    "Key": "RECORD_TYPE",
                                    "Values": self.config.filtered_costs
                                }
                            }},
                        **kwargs)
                else:
                    data = self.client.get_cost_and_usage(
                        TimePeriod={
                            'Start': start.isoformat(),
                            'End': end.isoformat()
                        },
                        Granularity=granularity,
                        Metrics=[
                            'UnblendedCost',
                        ],
                        GroupBy=groups,
                        **kwargs)

                results += data['ResultsByTime']
                token = data.get('NextPageToken')

                if not token:
                    self.cache.save(request_name, json.dumps(results))
                    break

        return results
