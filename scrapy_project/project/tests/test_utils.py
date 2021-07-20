from boto3.resources.base import ServiceResource


def test_build_proxycrawl(base_spider):
    url = base_spider.build_proxycrawl("http://example.com")
    assert "proxycrawl" in url
    assert "test-token" in url
    assert "example.com" in url


def test_get_url_from_proxycrawl(base_spider):
    url = base_spider.build_proxycrawl("http://example.com")
    assert "http://example.com" in base_spider.get_url_from_proxycrawl(url)


def test_build_request_proxycrawl(base_spider):
    request = base_spider.build_request("http://example.com", provider="proxycrawl")
    assert "proxycrawl" in request.url
    assert request.meta.get("proxy") is None
    assert request.errback is not None


def test_build_request_crawlera(base_spider):
    request = base_spider.build_request("http://example.com", provider="crawlera")
    assert "proxycrawl" not in request.url
    assert request.meta.get("proxy") is not None
    assert request.errback is not None


def test_s3_create_client(s3):
    obj = s3.create_client()
    assert "botocore.client.S3" in str(type(obj))


def test_s3_create_resource(s3):
    obj = s3.create_s3_resource()
    assert isinstance(obj, ServiceResource)
