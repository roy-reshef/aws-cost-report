import datetime
import logging
import os
from abc import ABC, abstractmethod
from time import sleep

import croniter

from costreport.analysis.analyzers import DataAnalyzer
from costreport.app_config import AppConfig, ReportType, ReportDestination, LocalDestination
from costreport.collection.aws.aws_collector import AwsCollector
from costreport.data_container import DataContainer
from costreport.data_provider import DataProvider
from costreport.output_manager import OutputManager
from costreport.report_generators.html_generator import HTMLReportGenerator
from costreport.utils import consts
from costreport.utils.cache_manager import RawDateCacheManager
from costreport.utils.date_utils import get_time

logger = logging.getLogger(__name__)

report_generators = {
    ReportType.HTML.value: HTMLReportGenerator
}


class ExecutorBase(ABC):

    def __init__(self, config: AppConfig):
        self.config = config

        # create local directory if local destination is configured
        if config.destinations.get(ReportDestination.LOCAL.value):
            local_dest: LocalDestination = config.destinations.get(ReportDestination.LOCAL.value)
            if not os.path.exists(local_dest.directory):
                os.makedirs(local_dest.directory)

    def _generate_reports(self):
        exec_time = get_time()
        reporter = DataProvider(exec_time, self.config, AwsCollector(self.config,
                                                                     exec_time,
                                                                     RawDateCacheManager(self.config,
                                                                                         "aws")))
        data_container: DataContainer = reporter.generate()
        DataAnalyzer(data_container).analyze()
        additional_data_items = {consts.ReportItemName.REPORT_TITLE.value: self.config.report_title}

        for report_cfg in self.config.reports:
            generator_cls = report_generators.get(report_cfg.name)
            if not generator_cls:
                raise Exception(f'unknown report name : {report_cfg.name}')
            output = generator_cls(data_container, report_cfg.report_config, self.config.filtered_services) \
                .generate(additional_data_items)
            output_manager = OutputManager(exec_time, self.config.destinations)
            output_manager.output(output)

    def exec(self):
        self._exec()

    @abstractmethod
    def _exec(self):
        raise NotImplementedError('_exec function should be implemented by subclasses')


class SingleExecutor(ExecutorBase):
    """

    """

    def _exec(self):
        logger.info('executing single report executor')
        self._generate_reports()


class ScheduledExecutor(ExecutorBase):
    """

    """

    @staticmethod
    def _round_time(dt=None):
        """
        floors datetime minute
        """
        if not dt:
            dt = datetime.datetime.now()

        return dt.replace(second=0, microsecond=0)

    def _exec(self):
        schedule = self.config.schedule
        if not schedule:
            raise Exception('expected schedule configuration!')
        logger.info(f'executing scheduled report executor with schedule {schedule}')

        # init croniter
        now = datetime.datetime.now()
        cron = croniter.croniter(schedule, now)

        while True:
            # get next execution time
            next_exec = cron.get_next(ret_type=datetime.datetime)
            logger.info(f'waiting until next exec time:{next_exec}')

            still_waiting = True
            while still_waiting:
                rounded_now = self._round_time()

                if rounded_now == next_exec:
                    self._generate_reports()
                    still_waiting = False
                else:
                    sleep(60)
