import json
import logging
from abc import ABC
from enum import Enum, unique
from typing import List, Dict

MONTHLY_REPORT_MONTHS_BACK_DEFAULT = 6
SERVICES_REPORT_DAYS_BACK_DEFAULT = 30
DAILY_REPORT_DAYS_BACK_DEFAULT = 30
TAGS_REPORT_DAYS_BACK_DEFAULT = 30

TEMPLATE_NAME_DEFAULT = "default.html"
REPORT_TITLE_DEFAULT = "AWS Costs Report"

logger = logging.getLogger(__name__)


class ConfigurationException(Exception):
    pass


class _PeriodsConfig:
    def __init__(self):
        self._monthly_report_months_back = MONTHLY_REPORT_MONTHS_BACK_DEFAULT
        self._services_report_days_back = SERVICES_REPORT_DAYS_BACK_DEFAULT
        self._daily_report_days_back = DAILY_REPORT_DAYS_BACK_DEFAULT
        self._tags_report_days_back = TAGS_REPORT_DAYS_BACK_DEFAULT

    @property
    def monthly_report_months_back(self):
        return self._monthly_report_months_back

    @monthly_report_months_back.setter
    def monthly_report_months_back(self, val):
        self._monthly_report_months_back = val

    @property
    def services_report_days_back(self):
        return self._services_report_days_back

    @services_report_days_back.setter
    def services_report_days_back(self, val):
        self._services_report_days_back = val

    @property
    def daily_report_days_back(self):
        return self._daily_report_days_back

    @daily_report_days_back.setter
    def daily_report_days_back(self, val):
        self._daily_report_days_back = val

    @property
    def tags_report_days_back(self):
        return self._tags_report_days_back

    @tags_report_days_back.setter
    def tags_report_days_back(self, val):
        self._tags_report_days_back = val


class ReportDestination(Enum):
    S3 = 's3'


class _ReportDestination(ABC):
    def __init__(self, dest: ReportDestination):
        self.destination = dest


class S3Destination(_ReportDestination):
    def __init__(self, bucket_name, object_name):
        super().__init__(ReportDestination.S3)
        self.bucket_name = bucket_name
        self.object_name = object_name


@unique
class ReportType(Enum):
    HTML = "html"


class Report:
    def __init__(self, name, report_config: Dict):
        self.name = name
        self.report_config = report_config


class Reports:
    def __init__(self, reports: List[Report]):
        self.reports = reports


class AppConfig:
    periods = _PeriodsConfig()
    destinations = {}

    def __init__(self):
        cfg = self._load_config()
        logger.info(f'Loaded config:{cfg}')
        self.report_title = REPORT_TITLE_DEFAULT if not cfg.get('report_title') else cfg['report_title']
        self.accounts = {} if not cfg.get('accounts') else cfg['accounts']
        self.filtered_services = [] if not cfg.get('filtered_services') else cfg['filtered_services']
        self.filtered_costs = [] if not cfg.get('filtered_costs') else cfg['filtered_costs']
        self.resource_tags = [] if not cfg.get('resource_tags') else cfg['resource_tags']
        self.use_cache = False if not cfg.get('use_cache') else cfg['use_cache']
        # self.template_name = TEMPLATE_NAME_DEFAULT if not cfg.get('template_name') else cfg['template_name']
        self.schedule = None if not cfg.get('schedule') else cfg['schedule']

        self.reports = self._load_reports_config(cfg.get('reports'))

        if cfg.get('periods'):
            self._load_periods_config(cfg['periods'])

        if cfg.get('destinations'):
            self._load_destinations(cfg['destinations'])

    @staticmethod
    def _load_reports_config(reports_cfg):
        if not reports_cfg:
            raise ConfigurationException('Missing reports configuration')

        valid_reports = [i.value for i in ReportType]

        reports: List[Report] = []
        for k, v in reports_cfg.items():
            if k not in valid_reports:
                raise ConfigurationException(f'unknown report type:{k}')
            reports.append(Report(k, v))

        return reports

    def _load_periods_config(self, periods_cfg):
        if periods_cfg.get('monthly_report_months_back'):
            self.periods.monthly_report_months_back = periods_cfg['monthly_report_months_back']

        if periods_cfg.get('services_report_days_back'):
            self.periods.services_report_days_back = periods_cfg['services_report_days_back']

        if periods_cfg.get('daily_report_days_back'):
            self.periods.daily_report_days_back = periods_cfg['daily_report_days_back']

        if periods_cfg.get('tags_report_days_back'):
            self.periods.tags_report_days_back = periods_cfg['tags_report_days_back']

    def _load_destinations(self, dest_cfg):
        if dest_cfg.get(ReportDestination.S3.value):
            bucket_name = dest_cfg[ReportDestination.S3.value].get('bucket_name', None)
            if not bucket_name:
                raise ConfigurationException(
                    f'Report {ReportDestination.S3.value} Destination missing bucket_name property')

            object_name = dest_cfg[ReportDestination.S3.value].get('object_name', None)
            if not object_name:
                raise ConfigurationException(
                    f'Report {ReportDestination.S3.value} Destination missing object_name property')

            self.destinations[ReportDestination.S3.value] = S3Destination(bucket_name, object_name)
        else:
            raise ConfigurationException(f'Unknown report destination - {dest_cfg}')

    @staticmethod
    def _load_config():
        try:
            with open('configuration.json', 'r') as c:
                configuration = c.read()

            return json.loads(configuration)
        except FileNotFoundError:
            logger.info("configuration file was not found. running with defualts")
            return {}
        except ConfigurationException as e:
            logger.error(f'error loading configuration file: {str(e)}')
