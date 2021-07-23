#!/usr/bin/env python

import datetime
import logging
import time

from sellgo_core.utils.formatter import formatted_date
from sellgo_core.webcrawl.cloud import AWS
from sellgo_core.webcrawl.proxies import ProxyCrawl
from sellgo_core.webcrawl.scrapers import AmazonScraper
from sellgo_core.webcrawl.scrapers import InvalidASINError, BadStatusCodeError, EmptyDocumentError


def __create_product_crawl_history__(item, product_id, datetime_now):
    """
        Returns a python dictionary which contains info regarding the product crawl, e.g. datetime of crawl.
        The conversion to a database model is left to the user to perform.
    """
    item['cdate'] = datetime_now
    item['udate'] = datetime_now
    item['product_id'] = product_id
    return item


class AmazonWebCrawl:
    proxy = None
    logger = None
    scraper = None
    upload_to_s3 = False
    aws = None
    aws_storage_bucket_name = 'some_default_bucket_name'

    def __init__(self, **kwargs):
        self.init_logger(logger=kwargs.get('logger', None))
        self.init_proxy(
            use_proxy=kwargs.get('use_proxy', False),
            proxy_token=kwargs.get('proxy_token', None)
        )
        self.init_scraper()
        self.upload_to_s3 = kwargs.get('upload_to_s3', False)
        self.aws_storage_bucket_name = kwargs.get('aws_storage_bucket_name', 'some_default_bucket_name')

    def init_logger(self, logger=None):
        if not logger:
            logger = logging.getLogger(__name__)
            logger.setLevel(level=logging.INFO)
        if logger is False:
            logger.disabled = True
        self.logger = logger
        self.logger.info('Logger initialized')

    def init_proxy(self, use_proxy, proxy_token):
        if use_proxy and proxy_token:
            self.proxy = ProxyCrawl(proxy_token)
            self.logger.info('Proxy initialized')
        else:
            self.logger.info('Proxy usage is disabled')

    def init_scraper(self):
        self.scraper = AmazonScraper(self.proxy)
        self.logger.info('Scraper initialized')

    def init_aws(self, aws_s3_access_key_id, aws_s3_secret_access_key, aws_region):
        if aws_s3_access_key_id and aws_s3_secret_access_key and aws_region:
            try:
                self.aws = AWS(aws_s3_access_key_id, aws_s3_secret_access_key, aws_region)
                self.logger.info('AWS Session initialized')
            except Exception as ex:
                self.logger.error('AWS Init Error: %s' % ex)
                self.logger.error('Upload HTML to S3 functionality is disabled')
        else:
            self.logger.info('Upload HTML to S3 functionality is disabled')

    def scrape(self, asin):
        item = None
        try:
            item = self.scraper.scrape(asin)
        except InvalidASINError:
            self.logger.error('[ERROR] ASIN# %s - Invalid - SKIP' % asin)
        except BadStatusCodeError as ex:
            self.logger.error('[ERROR] ASIN# %s - BadStatusCode: %s - SKIP' % (asin, ex))
        except EmptyDocumentError:
            self.logger.error('[ERROR] ASIN# %s - EmptyDocument - SKIP' % asin)
        finally:
            return item

    def scrape_offer_sellers_by_page(self, asin, page=1):
        item = None
        try:
            item = self.scraper.scrape_offer_sellers_by_page(asin, page)
        except InvalidASINError:
            self.logger.error('[ERROR] ASIN# %s - Invalid - SKIP' % asin)
        except BadStatusCodeError as ex:
            self.logger.error('[ERROR] ASIN# %s - BadStatusCode: %s - SKIP' % (asin, ex))
        except EmptyDocumentError:
            self.logger.error('[ERROR] ASIN# %s - EmptyDocument - SKIP' % asin)
        finally:
            return item

    def upload_to_s3(self, item, target_file_name, aws_storage_bucket_name=None):
        if not aws_storage_bucket_name:
            aws_storage_bucket_name = self.aws_storage_bucket_name

        if self.aws and item and target_file_name:
            try:
                self.aws.upload_to_s3(aws_storage_bucket_name, target_file_name, source_text=item['raw_html'])
                return True
            except Exception as ex:
                self.logger.error(ex)  # something is wrong if upload to s3 fails
                return False

    def crawl(self, products_to_crawl):
        """
            Crawl products on amazon, upload scraped HTML to s3, and return product crawl histories.
            :param products_to_crawl: a dictionary containing 'asin' and 'product_id', or a list of such dictionaries.
            :return: dictionary or list of dictionaries containing info on product crawl.
        """
        if not self.proxy and not self.scraper:
            # currently requires proxy and scraper to be initialized to run the webcrawl task
            self.logger.error("Proxy and scraper not initialized")
            return

        if not products_to_crawl or len(products_to_crawl) == 0:
            self.logger.warning("No products were passed in to crawl")
            return

        self.logger.info('Crawling ...')
        product_crawl_histories = []

        if not isinstance(products_to_crawl, list):
            products_to_crawl = [products_to_crawl]

        for product in products_to_crawl:
            if isinstance(product, dict):
                asin = product['asin']
                product_id = product['product_id']
            elif isinstance(product, object):
                asin = product.asin
                product_id = product.product_id

            # scrape
            _temp_time = time.time()
            item = self.scrape(asin)
            _scrape_time = int(time.time() - _temp_time)

            if not item:  # can't find item when scraping
                continue

            datetime_now = datetime.datetime.now()
            target_file_name = '%s-%s' % (asin, formatted_date(datetime_now))

            # upload HTML to S3, if applicable
            _s3_upload_time = 0
            if self.upload_to_s3:
                _temp_time = time.time()
                upload_s3_success = self.upload_to_s3(item, target_file_name)
                if upload_s3_success:
                    item['s3_file_name'] = target_file_name
                _s3_upload_time = int(time.time() - _temp_time)

            # create dict containing info on the product crawl
            product_crawl_history = __create_product_crawl_history__(item, product_id, datetime_now)
            product_crawl_histories.append(product_crawl_history)

            self.logger.info('ASIN# %s\n\tscrape time: %ss\n\ts3 upload time: %ss'
                             % (asin, _scrape_time, _s3_upload_time))

        if len(product_crawl_histories) == 1:
            product_crawl_histories = product_crawl_histories[0]

        return product_crawl_histories
