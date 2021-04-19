import logging
from datetime import datetime

from costreport.app_config import AppConfig, ReportDestination, S3Destination
from costreport.utils.consts import OUTPUT_DIR, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
from costreport.utils.date_utils import format_datetime, PATH_TIME_FORMAT
from costreport.s3_client import S3Client

logger = logging.getLogger(__name__)


class OutputManager:
    def __init__(self, exec_time: datetime, config: AppConfig):
        self.exec_time = exec_time
        self.config = config

    def output(self, report_html_str):
        # save local file and then per configured destination
        self._save_html_report(report_html_str)

        if self.config.destinations and self.config.destinations.get(ReportDestination.S3.value):
            self._upload_to_s3(self.config.destinations[ReportDestination.S3.value])

    def _get_report_file_name(self):
        return f'cost_report_{format_datetime(self.exec_time, PATH_TIME_FORMAT)}.html'

    def _get_report_path(self):
        return f'{OUTPUT_DIR}/{self._get_report_file_name()}'

    def _save_html_report(self, report_html_str):
        local_file_name = self._get_report_path()
        logger.info(f'saving generated report file as {local_file_name}')
        f = open(local_file_name, 'w')
        f.write(report_html_str)
        f.close()

    def _upload_to_s3(self, dest_config: S3Destination):
        if not dest_config.bucket_name:
            logger.error('s3 destination bucket name is not specified! aborting s3 upload')
            return

        s3_client = S3Client(region_name='us-east-1',
                             aws_access_key_id=AWS_ACCESS_KEY_ID,
                             aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

        s3_client.upload_file(self._get_report_path(),
                              dest_config.bucket_name,
                              dest_config.object_name)
