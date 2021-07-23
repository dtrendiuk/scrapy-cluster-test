import datetime
import json
import os
import urllib.parse as urlparse
from urllib.parse import parse_qs, quote, unquote

import boto3  # type: ignore
import s3fs
import scrapy


class S3:
    def __init__(self):
        self.bucket_region = os.getenv("BUCKET_REGION")

        # S3FS Config
        self.access_key = os.getenv("BUCKET_ACCESS_KEY")
        self.secret_key = os.getenv("BUCKET_SECRET_KEY")

    def create_client(self):
        session = boto3.Session()
        return session.client(
            "s3",
            region_name=self.bucket_region,
            endpoint_url=f"https://{self.bucket_region}.digitaloceanspaces.com",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )

    def create_s3_resource(self):
        s3 = boto3.resource(
            "s3",
            region_name=self.bucket_region,
            endpoint_url=f"https://{self.bucket_region}.digitaloceanspaces.com",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )
        return s3

    def upload_dataframe_to_s3(self, df, filename, bucket_name):

        # Can't uses .to_excel() due to some unknown errors
        bytes_to_write = df.to_csv(None, index=False).encode()
        fs = s3fs.S3FileSystem(
            key=self.access_key,
            secret=self.secret_key,
            client_kwargs={"endpoint_url": f"https://{self.bucket_region}.digitaloceanspaces.com"},
        )

        with fs.open(f"{bucket_name}/{filename}", "wb") as f:
            f.write(bytes_to_write)


def get_url_from_proxycrawl(url):
    parsed = urlparse.urlparse(url)
    url = parse_qs(parsed.query)["url"][0]
    return unquote(url)


def build_proxycrawl(url, api_key):
    url = quote(url)
    return f"https://api.proxycrawl.com/?token={api_key}&country=US&url={url}"


def build_proxycrawl_js(url, api_key):
    url = quote(url)
    return f"https://api.proxycrawl.com/?token={api_key}" f"&ajax_wait=true&page_wait=15000&url={url}"


class BaseSpider(scrapy.Spider):
    start_urls = []

    def __init__(self, _job, proxy, total_expected_len, data, *args, **kwargs):
        if not data:
            return None

        self._data = json.loads(data)
        self.proxy_credentials = json.loads(proxy)

        self.get_raw = self._data.get("get_raw")
        self.s3_upload = self._data.get("s3_upload")
        self._total_yield = 0
        self._job = _job
        self._project = "project"
        self._spider = self.name
        self._total_expected_len = total_expected_len

        super().__init__(*args, **kwargs)

    def build_request(self, url, provider="crawlera", crawlera_endpoint="proxy.crawlera.com:8010", **kwargs):
        proxy_auth = f"{self.proxy_credentials['crawlera']}:"
        crawlera_auth = f"http://{proxy_auth}@{crawlera_endpoint}"

        if provider == "crawlera":
            headers = {
                "X-Crawlera-Profile": "desktop",
                "X-Crawlera-Cookies": "disable",
            }

            meta = {
                "proxy": crawlera_auth,
                "crawlera": crawlera_auth,
                "proxycrawl": self.proxy_credentials["proxycrawl"],
                "proxycrawl_js": self.proxy_credentials["proxycrawl_js"],
            }
            if "meta" in kwargs:
                kwargs["meta"].update(meta)
            else:
                kwargs.update({"meta": meta})

            return scrapy.Request(
                url,
                headers=headers,
                **kwargs,
            )

        elif provider == "proxycrawl":
            url = build_proxycrawl(url, self.proxy_credentials["proxycrawl"])
            meta = {
                "crawlera": crawlera_auth,
                "proxycrawl": self.proxy_credentials["proxycrawl"],
                "proxycrawl_js": self.proxy_credentials["proxycrawl_js"],
            }

            if "meta" in kwargs:
                kwargs["meta"].update(meta)
            else:
                kwargs.update({"meta": meta})

            return scrapy.Request(
                url,
                **kwargs,
            )

        elif provider == "proxycrawl_js":
            url = build_proxycrawl_js(url, self.proxy_credentials["proxycrawl_js"])
            meta = {
                "crawlera": crawlera_auth,
                "proxycrawl": self.proxy_credentials["proxycrawl"],
                "proxycrawl_js": self.proxy_credentials["proxycrawl_js"],
            }

            if "meta" in kwargs:
                kwargs["meta"].update(meta)
            else:
                kwargs.update({"meta": meta})

            return scrapy.Request(
                url,
                **kwargs,
            )


def utc_datetime():
    return datetime.datetime.now(datetime.timezone.utc)


def safe_cast(val, to_type, default=None):
    try:
        return to_type(val)
    except (ValueError, TypeError):
        return default
