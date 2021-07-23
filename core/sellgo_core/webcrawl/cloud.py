import boto3


class AWS(object):
    def __init__(self, aws_access_key_id, aws_secret_access_key, region_name):
        # init session
        self.session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name
        )
        self.resources = {}

    def upload_to_s3(self, bucket_name,
                     target_file_name, source_file_path=None, source_text=None):
        resource = self._s3_resource()
        if source_file_path is not None:
            bucket = resource.Bucket(bucket_name)
            bucket.upload_file(source_file_path, bucket_name, target_file_name)
        elif source_text is not None:
            resource.Object(bucket_name, target_file_name).put(Body=source_text)
        else:
            raise Exception('either of params "source_file_path" or "source_text" is required')

    def _s3_resource(self):
        if 's3' not in self.resources:
            self.resources['s3'] = self.session.resource('s3')
        return self.resources['s3']
