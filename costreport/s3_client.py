import logging

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class S3Client:
    """
    utility class for AWS S3 operations
    """

    def __init__(self,
                 region_name,
                 aws_access_key_id,
                 aws_secret_access_key):

        self.region_name = region_name
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self._client = None
        self._resource = None

    @property
    def client(self):
        if not self._client:
            self._client = boto3.client(
                's3',
                region_name=self.region_name,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key)

        return self._client

    @property
    def resource(self):
        if not self._resource:
            self._resource = boto3.resource(
                's3',
                region_name=self.region_name,
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key)

        return self._resource

    def _is_bucket_exists(self, name) -> bool:
        return self.resource.Bucket(name) in self.resource.buckets.all()

    def _create_bucket(self, name):
        logger.info(f'creating bucket {name}')
        self.client.create_bucket(Bucket=name)

    def _create_bucket_if_not_exists(self, name):
        if not self._is_bucket_exists(name):
            self._create_bucket(name)
        else:
            logger.info(f'bucket {name} already exists')

    def upload_file(self, file_name, bucket_name: str, object_name=None):
        """Upload a file to an S3 bucket

        :param file_name: File to upload
        :param bucket_name: Bucket name to upload to
        :param object_name: S3 object name. If not specified then file_name is used
        :return: None
        """

        self._create_bucket_if_not_exists(bucket_name)

        # If S3 object_name was not specified, use file_name
        if not object_name:
            object_name = file_name

        try:
            self.client.upload_file(file_name, bucket_name, object_name)
        except ClientError as e:
            logging.error(f'error loading file {file_name} to s3. error:{str(e)}')
