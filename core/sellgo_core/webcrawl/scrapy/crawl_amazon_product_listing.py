import datetime
import logging
import math
import re
from multiprocessing import Process, cpu_count

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy_proxycrawl import ProxyCrawlRequest

from sellgo_core import AmazonMarketplacesConst
from sellgo_core.utils.parser import parse_amazon_product_listing_page
from sellgo_core.webcrawl.scrapy.constants import CrawlUrlsConst, ProxyCrawlConst
from sellgo_core.webcrawl.scrapy.exceptions import InvalidASINError, EmptyDocumentError
from sellgo_core.webcrawl.scrapy.scrapy_common_settings import common_settings
from sellgo_core.webcrawl.scrapy.utils import get_product_identifiers, update_spider_with_proxycrawl


def crawl(products_to_crawl, marketplace=AmazonMarketplacesConst.US, custom_settings=None, enable_proxycrawl=False,
          proxycrawl_token=None, enable_multiproc=False, multiproc_enable_threshold=100,
          multiproc_min_urls_per_proc=50, enable_s3=False, aws_access_key_id=None, aws_secret_access_key=None,
          aws_region=None, aws_bucket_name=None):
    """
    Crawls the Amazon product listing page using AmazonProductListingSpider based on Scrapy.
    :param products_to_crawl:
        A list of 1) asin strings, 2) dicts of asin & product_id, or 3) objects with asin & product_id
    :param marketplace:
        One of the country dicts in AmazonMarketplacesConst
    :param custom_settings:
        Custom Scrapy settings for the AmazonProductListingSpider.
    :param enable_proxycrawl:
        To use ProxyCrawl or not.
    :param proxycrawl_token:
        If enable_proxycrawl is True, a proxycrawl_token must be provided.
    :param enable_multiproc:
        If enable_multiproc is True, will attempt to use multiprocessing to speed up crawling.
    :param multiproc_enable_threshold:
        Minimum urls to begin using more than 1 process
    :param multiproc_min_urls_per_proc:
        Minimum urls each process should have
    :param enable_s3:
        store parsed items to json files in s3
    :param aws_access_key_id:
        Required for storing to s3.
    :param aws_secret_access_key:
        Required for storing to s3.
    :param aws_region:
        Required for storing to s3.
    :param aws_bucket_name:
        Required for storing to s3.
    :raise ValueError:
        If products_to_crawl is empty.
        If enable_proxycrawl is True and no proxycrawl_token is provided.
        If use_crawler is True and enable_proxycrawl is False.
        If use_crawler is True and no crawler_name is provided.
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(level=logging.INFO)

    if not (products_to_crawl and isinstance(products_to_crawl, list) and len(
            products_to_crawl) >= 1 and not get_product_identifiers(products_to_crawl[0]) == (None, None)):
        raise ValueError(
            "products_to_crawl must be provided as a list of " +
            "1) asin strings, 2) dicts of asin & product_id, or 3) objects with asin & product_id")

    updated_settings = common_settings.copy()

    update_spider_with_proxycrawl(AmazonProductListingSpider, updated_settings, enable_proxycrawl, proxycrawl_token)

    update_settings_with_s3(updated_settings, enable_s3, aws_access_key_id, aws_secret_access_key, aws_region,
                            aws_bucket_name)

    if custom_settings:
        updated_settings.update(custom_settings)

    AmazonProductListingSpider.custom_settings = updated_settings

    def start_crawl(spider, *args):
        crawler_process = CrawlerProcess()
        crawler_process.crawl(spider, *args)
        crawler_process.start()

    if enable_multiproc and len(products_to_crawl) >= multiproc_enable_threshold:
        ideal_num_proc = math.ceil(len(products_to_crawl) / multiproc_min_urls_per_proc)
        actual_num_proc = ideal_num_proc if ideal_num_proc < cpu_count() else cpu_count()
        chunk_size = math.ceil(len(products_to_crawl) / actual_num_proc)
        product_chunks = [products_to_crawl[x:x + chunk_size] for x in range(0, len(products_to_crawl), chunk_size)]

        def start_crawl_proc(*args):
            process = Process(target=start_crawl, args=args)
            process.start()
            return process

        # adjust download delay based on number of processes
        logger.info(f'Number of Scrapy Processes: {actual_num_proc}')
        AmazonProductListingSpider.custom_settings[
            'DOWNLOAD_DELAY'] = 1.0 / ProxyCrawlConst.MAX_REQUESTS_PER_SECOND * actual_num_proc

        map(lambda x: x.join(), [
            start_crawl_proc(AmazonProductListingSpider, chunk, marketplace) for chunk in
            product_chunks
        ])
    else:
        start_crawl(AmazonProductListingSpider, products_to_crawl, marketplace)


def update_settings_with_s3(updated_settings, enable_s3, aws_access_key_id, aws_secret_access_key, aws_region,
                            aws_bucket_name):
    if enable_s3:
        if not aws_access_key_id or not aws_secret_access_key or not aws_region or not aws_bucket_name:
            raise ValueError("aws_access_key_id, aws_secret_access_key, aws_region and aws_bucket_name"
                             " must be provided if enable_s3 is True")
        updated_settings.update({
            "ITEM_PIPELINES": {
                'sellgo_core.webcrawl.scrapy.S3Pipeline': 100,
            },
            'S3PIPELINE_URL': 's3://' + aws_bucket_name + '/{name}/raw/{uuid}.json',
            "AWS_ACCESS_KEY_ID": aws_access_key_id,
            "AWS_SECRET_ACCESS_KEY": aws_secret_access_key,
            "AWS_REGION": aws_region
        })


class AmazonProductListingSpider(scrapy.Spider):
    name = "amazonproductlisting"
    enable_proxycrawl = True

    # regular expressions
    PT_NON_NUMERALS = re.compile(r'\D+')
    PT_CUSTOMER_RATING = re.compile(r'([\d\.]+) out of 5 stars')
    PT_BSR = re.compile(r'#([\d].*) in (.*)')

    def __init__(self, products_to_crawl, marketplace, *args, **kwargs):
        self.products_to_crawl = products_to_crawl
        self.marketplace = marketplace
        super().__init__(*args, **kwargs)

    def start_requests(self):
        for product in self.products_to_crawl:
            asin, product_id = get_product_identifiers(product)
            url = CrawlUrlsConst.AMAZON_PRODUCT_DP_URL % (self.marketplace['extension'], asin)
            meta = {'product': product}

            if self.enable_proxycrawl:
                yield ProxyCrawlRequest(url, callback=self.handle_response, meta=meta)
            else:
                yield scrapy.Request(url, callback=self.handle_response, meta=meta)

    def handle_response(self, response):
        product = response.meta.get('product')
        asin, product_id = get_product_identifiers(product)

        if not response.text:
            raise EmptyDocumentError(asin)
        elif 'Page Not Found' in response.text:
            raise InvalidASINError(asin)

        parsed_item = self.parse_response(response)

        datetime_now = datetime.datetime.now()
        parsed_item['asin'] = asin
        parsed_item['product_id'] = product_id
        parsed_item['cdate'] = datetime_now
        parsed_item['udate'] = datetime_now

        yield parsed_item

    def parse_response(self, response):
        result = parse_amazon_product_listing_page(response.text)
        return result
