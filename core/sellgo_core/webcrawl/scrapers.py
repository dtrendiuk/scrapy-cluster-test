import re
import time
import urllib.parse

import requests

from sellgo_core.utils.constants import WebCrawlConst
from sellgo_core.utils.parser import parse_offer_sellers_page_count, \
    parse_amazon_product_listing_page, get_all_offers


class AmazonScraper(object):
    # constants
    MARKETPLACE_ID = 'ATVPDKIKX0DER'
    SELLERS_PAGE_SIZE = 10
    PRODUCT_DP_URL = 'https://www.amazon.com/dp/%s'
    PRODUCT_OFFERS_URL = 'https://www.amazon.com/gp/aod/ajax/ref=olp_aod_redir?asin={}&pc=dp'
    COMMON_HTTP_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)'
                      ' Chrome/69.0.3497.92 Safari/537.36'
    }

    # regular expressions
    PT_NON_NUMERALS = re.compile(r'\D+')
    PT_CUSTOMER_RATING = re.compile(r'([\d\.]+) out of 5 stars')
    PT_BSR = re.compile(r'#([\d].*) in (.*)')
    PT_NR_OF_SELLERS = re.compile(r'New \(([\d\.]+)\) from')

    def __init__(self, proxy=None):
        # init session
        self.session = requests.Session()

        # set up proxy with a new session
        self.proxy = proxy
        if self.proxy is not None:
            self.proxy.set_session(self.session)

    def scrape(self, asin):
        # prepare URL and proxy/session
        url = AmazonScraper.PRODUCT_DP_URL % asin
        target = self.proxy if self.proxy is not None else self.session

        # make request
        retry = 0
        while retry < WebCrawlConst.PROXYCRAWL_MAX_RETRY:
            response = target.get(url, headers=AmazonScraper.COMMON_HTTP_HEADERS)
            if 'Page Not Found' in response.text:
                raise InvalidASINError(asin)
            elif response.status_code != 200:
                retry += 1
                if retry == WebCrawlConst.PROXYCRAWL_MAX_RETRY:
                    raise BadStatusCodeError(response.status_code)
                time.sleep(WebCrawlConst.PROXYCRAWL_RETRY_SLEEP)
            elif not response.text:
                raise EmptyDocumentError()
            else:
                retry = WebCrawlConst.PROXYCRAWL_MAX_RETRY

        # extract data
        result = parse_amazon_product_listing_page(response.text)
        result['asin'] = asin

        return result

    def scrape_offer_sellers_by_page(self, asin, page=1):
        response = None
        url = urllib.parse.quote(self.PRODUCT_OFFERS_URL.format(asin))
        target = self.proxy if self.proxy is not None else self.session

        # Make request
        retry = 0
        while retry < WebCrawlConst.PROXYCRAWL_MAX_RETRY:
            response = target.get(url, headers=AmazonScraper.COMMON_HTTP_HEADERS)
            if 'Page Not Found' in response.text:
                raise InvalidASINError(asin)
            elif response.status_code != 200:
                retry += 1
                if retry == WebCrawlConst.PROXYCRAWL_MAX_RETRY:
                    raise BadStatusCodeError(response.status_code)
                time.sleep(WebCrawlConst.PROXYCRAWL_RETRY_SLEEP)
            elif not response.text:
                raise EmptyDocumentError()
            else:
                retry = WebCrawlConst.PROXYCRAWL_MAX_RETRY

        # sellers = parse_offer_sellers(response.text)
        sellers = get_all_offers(asin, response.text)

        page_count = None
        if page == 1:
            page_count = parse_offer_sellers_page_count(response.text)

        return sellers, page_count


class InvalidASINError(Exception):
    pass


class BadStatusCodeError(Exception):
    pass


class EmptyDocumentError(Exception):
    pass
