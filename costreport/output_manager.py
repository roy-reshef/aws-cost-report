import logging
from shutil import copyfile

from costreport.consts import OUTPUT_DIR, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, REGION_NAME
from costreport.date_utils import get_today
from costreport.s3_client import S3Client

logger = logging.getLogger(__name__)


class OutputManager:
    def __init__(self, config):
        self.config = config

    def output(self, report_html_str):
        # save local file and then per configured destination
        self._save_html_report(report_html_str)

        if self.config.get('destinations') and self.config['destinations'].get('s3'):
            self._upload_to_s3(self.config['destinations']['s3'])

    @staticmethod
    def _get_report_file_name():
        return f'cost_report_{get_today().isoformat()}.html'

    def _get_report_path(self):
        return f'{OUTPUT_DIR}/{self._get_report_file_name()}'

    def _save_html_report(self, report_html_str):
        local_file_name = self._get_report_path()
        logger.info(f'saving generated report file as {local_file_name}')
        f = open(local_file_name, 'w')
        f.write(report_html_str)
        f.close()

    def _upload_to_s3(self, dest_config):
        if not dest_config.get('bucket_name'):
            logger.error('s3 destination bucket name is not specified! aborting s3 upload')
            return

        s3_client = S3Client(region_name='us-east-1',
                             aws_access_key_id=AWS_ACCESS_KEY_ID,
                             aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

        s3_client.upload_file(self._get_report_path(),
                              dest_config.get('bucket_name'),
                              dest_config.get('object_name'))
