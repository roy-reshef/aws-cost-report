import logging
import os
import shutil
import uuid
from datetime import datetime

from costreport.app_config import ReportDestination, S3Destination, LocalDestination
from costreport.s3_client import S3Client
from costreport.utils.consts import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
from costreport.utils.date_utils import format_datetime, PATH_TIME_FORMAT

logger = logging.getLogger(__name__)


class OutputManager:
    def __init__(self, exec_time: datetime, dest_config):
        self.exec_time = exec_time
        self.dest_config = dest_config

    def output(self, report_html_str):
        if not self.dest_config:
            raise Exception('no configured report destinations')

        if self.dest_config.get(ReportDestination.LOCAL.value):
            self._save_html_report(self.dest_config[ReportDestination.LOCAL.value], report_html_str)

        if self.dest_config.get(ReportDestination.S3.value):
            self._upload_to_s3(self.dest_config[ReportDestination.S3.value], report_html_str)

    def _get_report_file_name(self):
        return f'cost_report_{format_datetime(self.exec_time, PATH_TIME_FORMAT)}.html'

    def _save_html_report(self, dest_config: LocalDestination, report_html_str):
        directory = dest_config.directory
        local_file_name = f'{directory}/{self._get_report_file_name()}'
        logger.info(f'saving generated report file as {local_file_name}')
        f = open(local_file_name, 'w')
        f.write(report_html_str)
        f.close()

    def _upload_to_s3(self, dest_config: S3Destination, report_html_str):
        if not dest_config.bucket_name:
            logger.error('s3 destination bucket name is not specified! aborting s3 upload')
            return

        s3_client = S3Client(region_name='us-east-1',
                             aws_access_key_id=AWS_ACCESS_KEY_ID,
                             aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

        object_key = f'{dest_config.object_key_prefix}/{self._get_report_file_name()}' if \
            dest_config.object_key_prefix else self._get_report_file_name()
        logger.info(f'uploading report to s3. bucket:{dest_config.bucket_name}. key: {object_key}')
        tmp_directory = str(uuid.uuid4())
        os.makedirs(tmp_directory)
        local_file_name = f'{tmp_directory}/{self._get_report_file_name()}'
        f = open(local_file_name, 'w')
        f.write(report_html_str)
        f.close()

        s3_client.upload_file(local_file_name,
                              dest_config.bucket_name,
                              object_key)

        shutil.rmtree(tmp_directory)
