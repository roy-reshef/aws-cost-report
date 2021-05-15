import datetime
import logging
from abc import ABC, abstractmethod
from time import sleep

import croniter

from costreport.app_config import AppConfig
from costreport.collection.aws.aws_collector import AwsCollector
from costreport.cost_report_generator import CostReporter
from costreport.layout_manager import LayoutManager
from costreport.output_manager import OutputManager
from costreport.utils import consts
from costreport.utils.cache_manager import RawDateCacheManager
from costreport.utils.date_utils import get_time

logger = logging.getLogger(__name__)


class ExecutorBase(ABC):

    def __init__(self, config: AppConfig):
        self.config = config

    def _generate_report(self):
        exec_time = get_time()
        # TODO: temporarily pass hardcoded connector name. once
        # once another connector is implemented and configuration will support multiple
        # connectors - take name from configuration

        reporter = CostReporter(exec_time, self.config, AwsCollector(self.config,
                                                                     exec_time,
                                                                     RawDateCacheManager(self.config,
                                                                                         "aws")))
        reporter.generate()

        data_items = {consts.ReportItemName.REPORT_TITLE.value: self.config.report_title}
        report_html_str = LayoutManager(reporter.item_defs, self.config).layout(data_items)

        output_manager = OutputManager(exec_time, self.config)
        output_manager.output(report_html_str)

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
        self._generate_report()


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
                    self._generate_report()
                    still_waiting = False
                else:
                    sleep(60)
