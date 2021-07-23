from boto3.resources.base import ServiceResource

from sellgo_core.webcrawl.cloud import AWS


def test_aws():
    aws = AWS('AQHSHDKKAJSJAJJ', 'sdkjkasJJKJSdksjdksad//asdasdjwi0jwek2d#', 'us-east-1')

    assert aws is not None
    assert aws.resources is not None
    assert isinstance(aws.resources, dict)

    s3 = aws.session.resource('s3')

    assert s3 is not None
    assert isinstance(s3, ServiceResource)
