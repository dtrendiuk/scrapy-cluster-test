"""
Scrape Amazon Sellers
"""
import re
import urllib.parse as urlparse
from urllib.parse import parse_qs

import pymongo
import scrapy
from sellgo_core.utils.parser import (  # type: ignore
    get_offers,
    get_pinned_offer,
)

from ..constants import AmazonMerchantAutoStats
from ..db import db
from ..middlewares import get_retry_request
from ..utils import get_url_from_proxycrawl, utc_datetime
from .amazon_merchant import AmazonMerchantSpider


class AmazonMerchantAutonomousSpider(AmazonMerchantSpider):
    name = "amazon_merchant_autonomous"
    custom_settings = {
        "DOWNLOAD_DELAY": 1 / 1000,
        "RETRY_HTTP_CODES": [404, 429, 503, 520],
        "RETRY_TIMES": 2,
        "DNSCACHE_ENABLED": False,
        "USER_AGENT": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)"
            " Chrome/69.0.3497.92 Safari/537.36"
        ),
        "LOG_LEVEL": "DEBUG",
        "DUPEFILTER_DEBUG": True,
        "DUPEFILTER_CLASS": "scrapy.dupefilters.BaseDupeFilter",
        "ITEM_PIPELINES": {
            "project.pipelines.AmazonMerchantAutonomousPipeline": 300,
            "project.pipelines.ProgressPipeline": 500,
        },
        "CONCURRENT_REQUESTS": 1500,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1500,
        "CONCURRENT_ITEMS": 500,
        "DOWNLOAD_TIMEOUT": 600,
        "EXTENSIONS": {"project.extensions.SentryLogging": -1},
        # FIFO
        "DEPTH_PRIORITY": 1,
        "SCHEDULER_DISK_QUEUE": "scrapy.squeues.PickleFifoDiskQueue",
        "SCHEDULER_MEMORY_QUEUE": "scrapy.squeues.FifoMemoryQueue",
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
            "project.middlewares.CustomRetryMiddleware": 550,
        },
        "SPIDER_MIDDLEWARES": {"scrapy.spidermiddlewares.referer.RefererMiddleware": None},
    }
    done_scrape = False

    def __init__(self, _job, proxy, total_expected_len, data, *args, **kwargs):
        super().__init__(_job, proxy, total_expected_len, data, *args, **kwargs)

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        from_crawler = super(AmazonMerchantSpider, cls).from_crawler
        spider = from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.idle, signal=scrapy.signals.spider_idle)  # type: ignore
        return spider

    def idle(self):
        if not self.done_scrape:
            # todo_asin
            collection = db["amazon_product"]
            todo_asins = collection.aggregate(
                [
                    {
                        "$match": {
                            "$and": [{"pending": True}],
                        }
                    },
                    {"$project": {"asin": 1, "created_at": 1}},
                    {"$sort": {"created_at": 1}},
                    {"$limit": 2000},
                ],
                allowDiskUse=True,
            )
            todo_asins = [(x["asin"], x.get("created_at")) for x in todo_asins]
            self.logger.debug(f"@idle -- todo_asins: {todo_asins}")

            collection = db["amazon_merchant_autonomous_todo_seller_id"]
            todo_seller_ids = collection.aggregate(
                [
                    {
                        "$match": {
                            "$and": [
                                {"pending": True},
                                {"private_label": {"$exists": True}},
                            ],
                        }
                    },
                    {"$sort": {"created_at": pymongo.ASCENDING}},
                    {"$limit": 5000},
                ],
                allowDiskUse=True,
            )
            requests = []

            for seller in todo_seller_ids:
                url = f"https://www.amazon.com/sp?seller={seller['seller_id']}"
                request = self.build_request(
                    url,
                    # provider="proxycrawl_js",
                    callback=self.parse_seller_data,
                    cb_kwargs={"private_label": seller.get("private_label")},
                    meta={
                        "proxycrawl_js_enabled": True,
                        "update_on_fail": {
                            "collection": "amazon_merchant_autonomous_todo_seller_id",
                            "key": "seller_id",
                            "seller_id": seller.get("seller_id"),
                            "update_values": {
                                "pending": False,
                                "last_scraped": utc_datetime().isoformat(),
                            },
                        },
                        "page_name": "seller-about",
                    },
                )
                requests.append(request)

            for asin, _ in todo_asins:
                # asin = record['asin']
                url = f"https://www.amazon.com/gp/aod/ajax/?asin={asin}&pc=dp&isonlyrenderofferlist=false&pageno=1"
                request = self.build_request(
                    url,
                    provider="proxycrawl",
                    callback=self.parse_via_asin,
                    meta={
                        "update_on_fail": {
                            "collection": "amazon_product",
                            "key": "asin",
                            "asin": asin,
                            "update_values": {
                                "pending": False,
                                "last_scraped": utc_datetime(),
                            },
                        },
                        "page_name": "offer-listing",
                    },
                )
                requests.append(request)

            for request in requests:
                self.crawler.engine.crawl(request, self)

            if not todo_asins and not todo_seller_ids:
                self.done_scrape = True

    def parse_via_asin(self, response, total_pages=1, total_offers=0, all_seller_ids=[]):
        url = response.request.url
        if "proxycrawl" in url:
            url = get_url_from_proxycrawl(url)

            key = f"{AmazonMerchantAutoStats.PROXYCRAWL_SUCCESS}/offer-listing"
            self.crawler.stats.inc_value(key)
            self.crawler.stats.inc_value(AmazonMerchantAutoStats.PROXYCRAWL_SUCCESS)
        else:
            key = f"{AmazonMerchantAutoStats.CRAWLERA_SUCCESS}/offer-listing"
            self.crawler.stats.inc_value(key)
            self.crawler.stats.inc_value(AmazonMerchantAutoStats.CRAWLERA_SUCCESS)

        url_params = urlparse.urlparse(url)
        url_params = parse_qs(url_params.query)

        asin = url_params["asin"]
        asin = asin[0] if asin else None

        sellers = get_offers(asin, raw_html=response.body)
        pinned_seller = get_pinned_offer(asin, response.body)

        if not (sellers or pinned_seller):
            yield get_retry_request(
                request=response.request.copy(), response=response, spider=self, reason="Empty sellers"
            )
            return None

        current_page = url_params["pageno"]
        current_page = int(current_page[0]) if current_page else 0

        current_page_seller_ids = []

        if current_page == 1:
            total_offers = response.css("#aod-total-offer-count").xpath("@value").get()
            total_offers = int(total_offers) if total_offers else 0

            if pinned_seller and not pinned_seller.get("amazon_as_seller"):
                self.logger.debug(f"@parse_via_asin -- asin: {asin}\npinned_seller: {pinned_seller}")
                # NOTE: Amazon as Seller won't be saved on DB
                # Because Amazon.com and Amazon Warehouse is already on our table
                url = pinned_seller.get("seller_url")
                url_params = urlparse.urlparse(url)
                url_params = parse_qs(url_params.query)

                seller_id = url_params.get("seller")  # type: ignore
                seller_id = seller_id[0] if seller_id else None
                if seller_id != "None" and current_page == 1:
                    current_page_seller_ids.append(seller_id)

            if pinned_seller:
                total_offers += 1

            if total_offers:
                if total_offers % 10 == 0:
                    total_pages = int(total_offers / 10)
                else:
                    total_pages = int(total_offers / 10) + 1

                self.logger.debug(
                    f"\n\n@parse_via_asin -- asin: {asin}\n"
                    f"total_offers: {total_offers}\ntotal_pages: {total_pages}\n\n"
                )

        for seller in sellers:
            # NOTE: Amazon as Seller will not be parse
            # Because Amazon.com and Amazon Warehouse is already on our table
            if seller and not seller.get("amazon_as_seller"):
                url = seller.get("seller_url")
                url_params = urlparse.urlparse(url)
                url_params = parse_qs(url_params.query)

                seller_id = url_params.get("seller")
                seller_id = seller_id[0] if seller_id else None
                if seller_id != "None":
                    current_page_seller_ids.append(seller_id)

        # Remove duplicate seller_id
        current_page_seller_ids = list(dict.fromkeys(current_page_seller_ids))

        # Unique seller ids starting from the page 1 till the current page.
        all_seller_ids = list(dict.fromkeys(set(all_seller_ids + current_page_seller_ids)))

        # Go to next page
        if current_page < total_pages:
            url = (
                f"https://www.amazon.com/gp/aod/ajax/?asin={asin}"
                f"&pc=dp&isonlyrenderofferlist=false&pageno={current_page + 1}"
            )
            yield self.build_request(
                url,
                provider="proxycrawl",
                callback=self.parse_via_asin,
                cb_kwargs={"all_seller_ids": all_seller_ids, "total_pages": total_pages, "total_offers": total_offers},
                meta={"page_name": "offer-listing"},
            )
            return None

        # SECTION: Analyze the data
        #          - private_label
        #          - num_offers
        #          - num_unique_sellers (Except Amazon)

        # Tag as private label
        # Note: There should not have Amazon.com nor Amazon Warehouse here
        private_label = False
        if len(all_seller_ids) <= 1:
            private_label = True
            self.crawler.stats.inc_value(AmazonMerchantAutoStats.PRIVATE_LABEL_ASINS_COUNT)
            self.crawler.stats.inc_value(AmazonMerchantAutoStats.PRIVATE_LABEL_PAGES_COUNT, current_page)

        data = {
            "jobid": self._job,
            "project": self._project,
            "spider": self._spider,
            "asin": asin,
            "yield_type": "from_parse_via_asin",
            "num_page": current_page,
            "num_offers": total_offers,
            "num_unique_sellers": len(all_seller_ids),
            "private_label": private_label,
            "seller_ids": all_seller_ids,
        }

        self.crawler.stats.inc_value(AmazonMerchantAutoStats.SCRAPED_ASINS_COUNT)
        yield data

    def parse_inventory_info(self, response, **kwargs):
        url = response.url
        if "proxycrawl" in url:
            url = get_url_from_proxycrawl(url)

            key = f"{AmazonMerchantAutoStats.PROXYCRAWL_SUCCESS}/seller-inventory"
            self.crawler.stats.inc_value(key)
            self.crawler.stats.inc_value(AmazonMerchantAutoStats.PROXYCRAWL_SUCCESS)
        else:
            key = f"{AmazonMerchantAutoStats.CRAWLERA_SUCCESS}/seller-inventory"
            self.crawler.stats.inc_value(key)
            self.crawler.stats.inc_value(AmazonMerchantAutoStats.CRAWLERA_SUCCESS)

        data = next(AmazonMerchantSpider.parse_inventory_info(self, response, **kwargs))
        data["yield_type"] = "from_parse_inventory_info"
        yield data

        seller_id = data["seller_id"]
        private_label = data["private_label"]

        # visit other pages
        pages = response.xpath("//ul[@class='a-pagination']")
        current_page = pages.xpath("//li[@class='a-selected']").css("::text").get()
        current_page = int(current_page) if current_page else None

        max_page_num = "".join(pages.xpath("//li[@class='a-disabled']").css("::text").extract())
        max_page_num = re.sub(r"\D", "", max_page_num)

        button_pages = pages.xpath("//li[@class='a-normal']").css("::text").extract()
        button_pages = list(map(int, button_pages))

        if current_page == 1:
            for num_page in button_pages:
                url = f"https://www.amazon.com/s?me={seller_id}&page={num_page}"
                yield self.build_request(
                    url,
                    callback=self.parse_next_inventory_page,
                    cb_kwargs={"private_label": private_label, "num_page": num_page},
                    meta={"page_name": "seller-inventory"},
                )

            if max_page_num:
                next_pages = [page for page in range(2, int(max_page_num) + 1) if page not in button_pages]
                for num_page in next_pages:
                    url = f"https://www.amazon.com/s?me={seller_id}&page={num_page}"
                    yield self.build_request(
                        url,
                        callback=self.parse_next_inventory_page,
                        cb_kwargs={"private_label": private_label, "num_page": num_page},
                        meta={"page_name": "seller-inventory"},
                    )

    def parse_next_inventory_page(self, response, num_page, private_label=False):
        asins = self.get_asins_from_inventory(response.body)
        data = {
            "jobid": self._job,
            "project": self._project,
            "spider": self._spider,
            "total_expected_len": self._total_expected_len,
            # "scraped_items_len": self._total_yield,
            "asins": asins,
            "private_label": private_label,
            "yield_type": "parse_next_inventory_page",
            "num_page": num_page,
        }
        yield data

        self.logger.info(f"@parse_next_inventory_page: \ndata = {data}\n\n")

    def parse_seller_data(self, response, *args, **kwargs):
        url = response.url
        if "proxycrawl" in url:
            url = get_url_from_proxycrawl(url)

            key = f"{AmazonMerchantAutoStats.PROXYCRAWL_SUCCESS}/seller-about"
            self.crawler.stats.inc_value(key)
            self.crawler.stats.inc_value(AmazonMerchantAutoStats.PROXYCRAWL_SUCCESS)
        else:
            key = f"{AmazonMerchantAutoStats.CRAWLERA_SUCCESS}/seller-about"
            self.crawler.stats.inc_value(key)
            self.crawler.stats.inc_value(AmazonMerchantAutoStats.CRAWLERA_SUCCESS)

        return super().parse_seller_data(response, *args, **kwargs)

    def closed(self, _):
        stats = self.crawler.stats
        total_success_pages_200 = stats.get_value("downloader/response_status_count/200")

        duration_min = int(stats.get_value("elapsed_time_seconds") / 60)
        if duration_min == 0:
            duration_min = 1

        speed_pages_per_min = 0
        if total_success_pages_200 and duration_min:
            speed_pages_per_min = int(total_success_pages_200 / duration_min)

        data = {
            "start_datetime": stats.get_value("start_time"),
            "duration_min": duration_min,
            "total_success_pages_200": total_success_pages_200,
            "total_failed_requests_503": stats.get_value("downloader/response_status_count/503"),
            "total_failed_requests_520": stats.get_value("downloader/response_status_count/520"),
            "total_scraped_asins": stats.get_value("result/scraped_asins_count"),
            "total_skipped_asins": stats.get_value("result/asins_with_zero_new_sellers_count"),
            "total_asins_private_label": stats.get_value("result/private_label_asins_count"),
            "total_new_seller_ids": stats.get_value("result/inserted_seller_id_count"),
            "total_new_seller_ids_non_private_label": stats.get_value(
                "result/inserted_non_private_label_seller_id_count"
            ),
            "total_new_seller_ids_private_label": stats.get_value("result/inserted_private_label_seller_id_count"),
            "speed_pages_per_min": speed_pages_per_min,
        }
        collection = db["seller_autonomous_stats"]
        collection.insert_one(data)
