"""
Scrape Amazon Seller Inventory
"""
import re
import urllib.parse as urlparse
from urllib.parse import parse_qs

import scrapy

from ..middlewares import get_retry_request
from ..utils import BaseSpider


class AmazonMerchantInventorySpider(BaseSpider):
    name = "amazon_merchant_inventory"
    custom_settings = {
        "DOWNLOAD_DELAY": 1 / 40,
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
            "project.pipelines.SellerInventoryPipeline": 300,
            "project.pipelines.MongoPipeline": 400,
            "project.pipelines.ProgressPipeline": 500,
        },
        "CONCURRENT_REQUESTS": 32,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 32,
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

    def __init__(self, _job, proxy, total_expected_len, data, *args, **kwargs):
        super().__init__(_job, proxy, total_expected_len, data, *args, **kwargs)

        if not data:
            return None

        seller_ids = self._data.get("seller_ids")

        if seller_ids:
            _urls = ["https://www.amazon.com/s?me=" f"{seller_id}" for seller_id in seller_ids]
            self.start_urls.extend(_urls)

    def start_requests(self):
        for url in self.start_urls:
            yield self.build_request(url)

    def get_product_data(self, product_raw):
        selector = scrapy.Selector(text=product_raw)
        is_fba = selector.xpath("//i[contains(@class, 'a-icon-prime')]").extract_first()

        product_url = selector.xpath("//a[@class='a-link-normal a-text-normal']/@href").extract_first()

        product_name = selector.xpath(
            "//span[@class='a-size-medium a-color-base a-text-normal']/text()"
        ).extract_first()

        current_price = selector.xpath("//span[@class='a-price']").css("::text").extract_first()

        original_price = selector.xpath("//span[@class='a-price a-text-price']").css("::text").extract_first()

        best_seller = selector.xpath(
            "//span[@class='a-badge-text' and contains(text(), 'Best Seller')]"
        ).extract_first()
        best_seller = True if best_seller else False

        amazon_choice = selector.xpath(
            "//span[@class='a-badge-text' and contains(text(), 'Amazon Choice')]"
        ).extract_first()
        amazon_choice = True if amazon_choice else False

        reviews_count = (
            selector.xpath(
                "//div[@class='a-section a-spacing-none " "a-spacing-top-micro']//span[@class='a-size-base']"
            )
            .css("::text")
            .extract_first()
        )
        review_stars = selector.xpath("//a[@class='a-popover-trigger a-declarative']/i/span").css("::text").get()
        review_stars = float(review_stars[:-15]) if review_stars else None

        save_and_subscribe = selector.xpath(
            "//span[contains(text(), 'Save more with Subscribe & Save')]"
        ).extract_first()
        save_and_subscribe = True if save_and_subscribe else False

        variation = selector.xpath("//span[contains(text(), 'Price may vary by')]").get()
        variation = True if variation else False

        category = selector.xpath("//a[@class='a-size-base a-link-normal a-text-bold']").css("::text").get()
        category = category.strip() if category else None

        # Get the ASIN from the URL
        asin_re = re.search(r"\b(dp/)\b", product_url)  # type: ignore
        start_asin_index = asin_re.start() + 3

        asin_partial = product_url[start_asin_index:]
        end_asin_index = asin_partial.rindex("/")

        asin = asin_partial[:end_asin_index]

        product_url = f"https://www.amazon.com{product_url}"
        product_data = {
            "jobid": self._job,
            "project": self._project,
            "spider": self._spider,
            "total_expected_len": self._total_expected_len,
            "scraped_items_len": self._total_yield,
            "asin": asin,
            "product_name": product_name,
            "product_url": product_url,
            "current_price": current_price,
            "original_price": original_price,
            "best_seller": best_seller,
            "amazon_choice": amazon_choice,
            "reviews_count": reviews_count,
            "review_stars": review_stars,
            "save_and_subscribe": save_and_subscribe,
            "variation": variation,
            "category": category,
            "marketplace_id": "ATVPDKIKX0DER",
        }

        if is_fba:
            product_data["fba"] = True
            product_data["fbm"] = False

        else:
            product_data["fba"] = False
            product_data["fbm"] = True

        return product_data

    def get_inventory_count(self, response_raw):
        response = scrapy.Selector(text=response_raw)

        ic = response.xpath("//span[@class='celwidget slot=UPPER template=RESULT_INFO_BAR widgetId=result-info-bar']")
        ic = ic.xpath("//span[contains(text(),'result')]").css("::text").get()

        inventory_count = 0
        if ic and "over" in ic:
            # index of `r` in `of over`
            ic_index_r = ic.index("r") + 1
            ic_partial = ic[ic_index_r:]

            # index of `r` in `results`
            ic_index_r = ic_partial.index("r")
            inventory_count = ic_partial[:ic_index_r]

            # extract integers
            inventory_count = "".join(filter(str.isdigit, inventory_count))
        elif ic and "of" in ic:
            # index of `f` in `of`
            ic_index_f = ic.index("f") + 1
            ic_partial = ic[ic_index_f:]

            # index of `r` in `results`
            ic_index_r = ic_partial.index("r")
            inventory_count = ic_partial[:ic_index_r]

            # extract integers
            inventory_count = "".join(filter(str.isdigit, inventory_count))
        elif ic:
            # extract integers
            inventory_count = "".join(filter(str.isdigit, ic))

        if inventory_count != 0:
            inventory_count = int(re.sub("[^0-9]", "", inventory_count))  # type: ignore

        return inventory_count

    @staticmethod
    def get_products(response_raw):
        response = scrapy.Selector(text=response_raw)
        return response.xpath("//div[@class='a-section a-spacing-medium']").extract()

    def parse(self, response):
        proxy_url = response.request.url
        if "proxycrawl" in proxy_url:
            url = self.get_url_from_proxycrawl(proxy_url)
        else:
            url = proxy_url

        url_params = urlparse.urlparse(url)
        url_params = parse_qs(url_params.query)

        products = self.get_products(response.body)

        if not products:
            yield get_retry_request(
                request=response.request.copy(), response=response, spider=self, reason="Empty inventory"
            )
            return None

        seller_id = url_params["me"]
        seller_id = seller_id[0] if seller_id else None

        inventory_count = self.get_inventory_count(response.body)

        for product in products:
            product_data = self.get_product_data(product)

            product_data["inventory_link"] = url
            product_data["inventory_count"] = inventory_count
            product_data["seller_link"] = f"https://www.amazon.com/sp?seller={seller_id}"
            product_data["seller_id"] = seller_id

            self._total_yield += 1
            yield product_data

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
                yield self.build_request(url)

            if max_page_num:
                next_pages = [page for page in range(2, int(max_page_num) + 1) if page not in button_pages]
                for num_page in next_pages:
                    url = f"https://www.amazon.com/s?me={seller_id}&page={num_page}"
                    yield self.build_request(url)
