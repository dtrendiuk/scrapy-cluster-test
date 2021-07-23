import pytest
from project.utils import S3, BaseSpider  # type: ignore


# Breaking because: https://github.com/dask/s3fs/issues/465
@pytest.fixture
def base_spider():
    obj = BaseSpider(
        _job="test",
        proxy=None,
        total_expected_len=0,
        data=None,
    )
    obj.proxy_credentials = {"proxycrawl": "test-token", "crawlera": "test-token"}
    return obj


@pytest.fixture
def s3():
    obj = S3()
    obj.bucket_region = "sfo2"
    obj.access_key = "test-access-key"
    obj.secret_key = "test-secret-key"
    return obj
