import boto3
import os
import logging
from botocore.exceptions import ClientError
import environ
env = environ.Env()
environ.Env.read_env()
logger = logging.getLogger(__name__)


class s3Client:
    BUCKET = env('BUCKET')

    session = boto3.session.Session()
    s3_client = session.client('s3',
                               region_name='nyc3',
                               endpoint_url=env('SPACES_ENDPOINT_FULL'),
                               aws_access_key_id=env('SPACES_KEY'),
                               aws_secret_access_key=env('SPACES_SECRET'),

                               )

    def __init__(self):
        pass

    def list_spaces(self):
        pass

    def upload(self, file, file_kind, parent_id, filename):
        """Upload a file to an S3 bucket

        :param file_name: File to upload
        :param file_kind: Kind of file: gyms, classes, workouts file
        :param parent_id: Id of the parent entity. Gym id, class id, or workout id.
        :return: True if file was uploaded, else False
        """
        # If S3 object_name was not specified, use file_name

        try:

            response = self.s3_client.put_object(
                Bucket=self.BUCKET,
                Key=f'{file_kind}/{parent_id}/{filename}',
                Body=file,
                ACL='public-read',
                Metadata={
                    'mykey': "myvalue"
                }
            )
            logger.debug("S3 upload response=%s", response)
        except ClientError as e:
            logger.warning("S3 upload client error: %s", e)
            return False
        return True

    def download(self):
        self.s3_client.download_file(self.BUCKET, 'OBJECT_NAME', 'FILE_NAME')

    def get_url(self):
        pass

    def remove(self, file_kind, parent_id, filename):
        logger.debug("Removing S3 object file_kind=%s parent_id=%s filename=%s", file_kind, parent_id, filename)
        try:
            response = self.s3_client.delete_object(
                Bucket=self.BUCKET,
                Key=f'{file_kind}/{parent_id}/{filename}',
            )
            logger.debug("S3 delete response=%s", response)
        except ClientError as e:
            logger.warning("Failed removing S3 object: %s", e)
            return False
        return True
