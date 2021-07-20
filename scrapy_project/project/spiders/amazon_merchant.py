"""
Scrape Amazon Sellers
"""
import json
import re
import urllib.parse as urlparse
from urllib.parse import parse_qs

import scrapy
from sellgo_core.utils.parser import get_offers, get_pinned_offer  # type:ignore

from ..constants import AmazonMerchantAutoStats
from ..db import db
from ..middlewares import get_retry_request
from ..utils import BaseSpider, get_url_from_proxycrawl, safe_cast


class AmazonMerchantSpider(BaseSpider):
    name = "amazon_merchant"
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
            "project.pipelines.MongoPipeline": 300,
            "project.pipelines.SellersSpiderPipeline": 400,
            "project.pipelines.ProgressPipeline": 500,
        },
        "CONCURRENT_REQUESTS": 50,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 50,
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

    result = []

    def __init__(self, _job, proxy, total_expected_len, data, *args, **kwargs):
        super().__init__(_job, proxy, total_expected_len, data, *args, **kwargs)

        if not data:
            return None

        seller_ids = self._data.get("seller_ids")
        asins = self._data.get("asins")

        if seller_ids:
            _urls = ["https://www.amazon.com/sp?seller=" f"{seller_id}" for seller_id in seller_ids]
            self.start_urls.extend(_urls)

        if asins:
            _urls = [
                f"https://www.amazon.com/gp/aod/ajax/?asin={asin}&pc=dp&isonlyrenderofferlist=false&pageno=1"
                for asin in asins
            ]
            self.start_urls.extend(_urls)

        collection = db["us_states"]
        self.us_states = [{"state": x["state"], "code": x["code"]} for x in collection.find()]

    def start_requests(self):
        for url in self.start_urls:
            # parse via asin
            if "asin=" in url:
                yield self.build_request(
                    url,
                    provider="proxycrawl",
                    callback=self.parse_via_asin,
                )

            # parse via seller_id
            elif "seller=" in url:
                yield self.build_request(
                    url,
                    callback=self.parse_seller_data,
                    cb_kwargs={"private_label": None},
                    meta={"proxycrawl_js_enabled": True},
                )

    def parse_via_asin(self, response):
        # parsing seller urls
        url = response.request.url
        if "proxycrawl" in url:
            url = get_url_from_proxycrawl(url)
            self.crawler.stats.inc_value(AmazonMerchantAutoStats.PROXYCRAWL_SUCCESS.format("offer-listing"))
        else:
            self.crawler.stats.inc_value(AmazonMerchantAutoStats.CRAWLERA_SUCCESS.format("offer-listing"))

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
        current_page = int(current_page[0]) if current_page else None

        total_offers = response.css("#aod-total-offer-count").xpath("@value").get()
        total_offers = int(total_offers) if total_offers else 0

        total_pages = 0

        if current_page == 1:
            if pinned_seller:
                total_offers += 1

            # Grab the pinned seller
            if pinned_seller:
                self.logger.debug(f"@parse_via_asin -- asin: {asin}\npinned_seller: {pinned_seller}")
                sellers.append(pinned_seller)

            if total_offers:
                if total_offers % 10 == 0:
                    total_pages = int(total_offers / 10)
                else:
                    total_pages = int(total_offers / 10) + 1

                # Create requests for all remaining pages
                for page in range(2, total_pages + 1):
                    url = (
                        f"https://www.amazon.com/gp/aod/ajax/?asin={asin}"
                        f"&pc=dp&isonlyrenderofferlist=false&pageno={page}"
                    )
                    yield self.build_request(
                        url,
                        provider="proxycrawl",
                        callback=self.parse_via_asin,
                    )

                self.logger.debug(
                    f"\n\n@parse_via_asin -- asin: {asin}\n"
                    f"total_offers: {total_offers}\ntotal_pages: {total_pages}\n\n"
                )

        # remove seller_id duplicates
        sellers = list({item["seller_id"]: item for item in sellers}.values())

        # Remove Amazon.com and Amazon Warehouse
        removed_amazon_as_sellers = []
        for seller in sellers:
            if not seller.get("amazon_as_seller"):
                removed_amazon_as_sellers.append(seller)

        private_label = False
        if len(removed_amazon_as_sellers) == 1 and not total_pages >= 2 and current_page == 1:
            private_label = True

        if private_label:
            self.crawler.stats.inc_value(AmazonMerchantAutoStats.PRIVATE_LABEL_ASINS_COUNT)

        for seller in removed_amazon_as_sellers:
            self.logger.debug(f"@parse_via_asin -- asin: {asin}\nother seller: {seller}\n")
            url = seller.get("seller_url")
            yield self.build_request(
                url=url,
                callback=self.parse_seller_data,
                cb_kwargs={"private_label": private_label},
                meta={"proxycrawl_js_enabled": True},
            )

    def get_asins_from_inventory(self, raw_html):
        response = scrapy.Selector(text=raw_html)
        products = response.xpath("//div[@class='a-section a-spacing-medium']").extract()
        asins = []
        for product in products:
            selector = scrapy.Selector(text=product)

            url = selector.xpath("//a[@class='a-link-normal a-text-normal']/@href").extract_first()

            # Get the ASIN from the URL
            asin_re = re.search(r"\b(dp/)\b", url)  # type: ignore
            start_asin_index = asin_re.start() + 3

            asin_partial = url[start_asin_index:]  # type: ignore
            end_asin_index = asin_partial.rindex("/")

            asin = asin_partial[:end_asin_index]
            if asin:
                asins.append(asin)

        return asins

    def get_inventory_info(self, raw_html):
        response = scrapy.Selector(text=raw_html)
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

        brands = (
            response.xpath(
                "//div[@id='brandsRefinements']"
                "//span[@class='a-size-base a-color-base' and not(contains(text(), 'Brand'))]"
            )
            .css("::text")
            .extract()
        )
        asins = self.get_asins_from_inventory(raw_html)
        data = {
            "inventory_count": inventory_count,
            "brands": brands,
            "asins": asins,
        }
        return data

    def parse_inventory_info(self, response, **kwargs):
        url = response.url
        if "proxycrawl" in url:
            url = get_url_from_proxycrawl(url)
            self.crawler.stats.inc_value(AmazonMerchantAutoStats.PROXYCRAWL_SUCCESS.format("seller-inventory"))
        else:
            self.crawler.stats.inc_value(AmazonMerchantAutoStats.CRAWLERA_SUCCESS.format("seller-inventory"))

        inventory_data = self.get_inventory_info(response.body)
        self._total_yield += 1

        data = {
            "jobid": self._job,
            "project": self._project,
            "spider": self._spider,
            "total_expected_len": self._total_expected_len,
            "scraped_items_len": self._total_yield,
        }
        data.update(inventory_data)
        data.update(kwargs)

        yield data

    def get_seller_data(self, url, raw_html):
        response = scrapy.Selector(text=raw_html)
        url_params = urlparse.urlparse(url)
        url_params = parse_qs(url_params.query)

        seller_id = url_params.get("seller")
        seller_id = seller_id[0] if seller_id else None

        asin = url_params.get("asin")
        asin = asin[0] if asin else None

        fba = url_params.get("isAmazonFulfilled")
        fba = fba[0] if fba else None

        marketplace_id = url_params.get("marketplaceID")
        marketplace_id = marketplace_id[0] if marketplace_id else None

        seller_name = response.css("h1[id='sellerName']").css("::text").extract_first()
        seller_logo = response.xpath("//img[@id='sellerLogo']/@src").get()

        try:
            business_name = (
                response.css("ul[class='a-unordered-list a-nostyle a-vertical']")
                .css("li span")[0]
                .css("::text")
                .extract()[1]
            )
        except Exception:
            business_name = None

        try:
            business_addresses = (
                response.css("ul[class='a-unordered-list a-nostyle a-vertical']")[1].css("li").css("::text").extract()
            )

        except Exception:
            business_addresses = None

        try:
            address = business_addresses[:-4]  # type: ignore
            address = " ".join(address)
        except Exception:
            address = None

        try:
            city = business_addresses[-4]  # type: ignore
        except Exception:
            city = None

        try:
            state = business_addresses[-3]  # type: ignore
        except Exception:
            state = None

        try:
            zip_code = business_addresses[-2]  # type: ignore
        except Exception:
            zip_code = None

        try:
            country = business_addresses[-1]  # type: ignore
        except Exception:
            country = None

        phone = response.css("span[id='seller-contact-phone']").css("::text").get()

        # front_url = response.css("div[id='storefront-link'] a").xpath("@href").get()

        seller_rating = response.css("span[class='a-icon-alt']").css("::text").get()
        if seller_rating:
            index_o = seller_rating.index("o")
            seller_rating = seller_rating[:index_o]

        review_ratings = response.css("b").css("::text").get()
        if review_ratings:
            review_ratings = "".join(filter(str.isdigit, review_ratings))
            review_ratings = f"{review_ratings}"

        rating_table = response.css("table[id='feedback-summary-table']")

        table_heading = rating_table.css("th[class='a-text-right']")
        positive_rating = rating_table.css("span[class='a-color-success']")
        neutral_rating = rating_table.css("span[class='a-color-secondary']")
        negative_rating = rating_table.css("span[class='a-color-error']")

        # Positive Table
        positive_data = [
            {heading.css("::text").get(): rating.css("::text").get()}
            for heading, rating in zip(table_heading, positive_rating)
        ]

        try:
            positive_30_days = positive_data[0]["30 days"]
        except Exception:
            positive_30_days = None

        try:
            positive_90_days = positive_data[1]["90 days"]
        except Exception:
            positive_90_days = None

        try:
            positive_12_month = positive_data[2]["12 months"]
        except Exception:
            positive_12_month = None

        try:
            positive_lifetime = positive_data[3]["Lifetime"]
        except Exception:
            positive_lifetime = None

        # Neutral Ratings
        neutral_data = [
            {heading.css("::text").get(): rating.css("::text").get()}
            for heading, rating in zip(table_heading, neutral_rating)
        ]

        try:
            neutral_30_days = neutral_data[0]["30 days"]
        except Exception:
            neutral_30_days = None

        try:
            neutral_90_days = neutral_data[1]["90 days"]
        except Exception:
            neutral_90_days = None

        try:
            neutral_12_month = neutral_data[2]["12 months"]
        except Exception:
            neutral_12_month = None

        try:
            neutral_lifetime = neutral_data[3]["Lifetime"]
        except Exception:
            neutral_lifetime = None

        # Negative Ratings
        negative_data = [
            {heading.css("::text").get(): rating.css("::text").get()}
            for heading, rating in zip(table_heading, negative_rating)
        ]
        try:
            negative_30_days = negative_data[0]["30 days"]
        except Exception:
            negative_30_days = None

        try:
            negative_90_days = negative_data[1]["90 days"]
        except Exception:
            negative_90_days = None

        try:
            negative_12_month = negative_data[2]["12 months"]
        except Exception:
            negative_12_month = None

        try:
            negative_lifetime = negative_data[3]["Lifetime"]
        except Exception:
            negative_lifetime = None

        # Count Table
        try:
            count_row = rating_table.css("tr")[4].css("::text").extract()
            count_30_days = int("".join(filter(str.isdigit, count_row[1])))
            count_90_days = int("".join(filter(str.isdigit, count_row[2])))
            count_12_month = int("".join(filter(str.isdigit, count_row[3])))
            count_lifetime = int("".join(filter(str.isdigit, count_row[4])))

        except Exception:
            count_30_days = None
            count_90_days = None
            count_12_month = None
            count_lifetime = None

        if count_12_month and int(count_12_month) != 0:
            launched = ">1Y"
        elif count_90_days and int(count_90_days) != 0:
            launched = "90D-1Y"
        elif count_30_days and int(count_30_days) != 0:
            launched = "30D-90D"
        else:
            launched = "<30D"

        inventory_link = response.xpath("//li[@id='products-link']/a").xpath("@href").get()
        if inventory_link:
            inventory_link = f"https://www.amazon.com{inventory_link}"
        else:
            inventory_link = ""

        # Feedback
        feeback_table = response.xpath("//table[@id='feedback-table']//tr")
        feedback_data = []

        for feedback in feeback_table:
            stars = feedback.xpath('//span[@class="a-icon-alt"]').css("::text").get()
            comment = feedback.css("#-text::text").get()
            comment_by = (
                feedback.xpath('//span[@class="a-size-base ' 'a-color-secondary feedback-rater"]').css("::text").get()
            )

            data = {"stars": stars, "comment": comment, "comment_by": comment_by}
            feedback_data.append(data)

        is_isbn = False
        try:
            if asin and int(asin[0]):
                is_isbn = True
        except ValueError:
            pass

        if str(country).upper() == "US":
            if state:
                state = str(state).replace(".", "")
                state = state.title()

                for x in self.us_states:
                    if len(state) == 2:
                        if state.upper() == x["code"]:
                            state = x["code"]
                            break

                    if state == x["state"]:
                        state = x["code"]
                        break

        data = {
            "inventory_link": inventory_link,
            "seller_link": url,
            "asin": asin,
            "is_isbn": is_isbn,
            "seller_id": seller_id,
            "seller_name": seller_name,
            "seller_logo": seller_logo,
            "business_name": business_name,
            "address": address,
            "city": city,
            "state": state,
            "zip_code": zip_code,
            "country": country,
            "phone": phone,
            "seller_rating": safe_cast(seller_rating, float),
            "review_ratings": safe_cast(review_ratings, int),
            "positive_30_days": safe_cast(positive_30_days, int),
            "positive_90_days": safe_cast(positive_90_days, int),
            "positive_12_month": safe_cast(positive_12_month, int),
            "positive_lifetime": safe_cast(positive_lifetime, int),
            "neutral_30_days": safe_cast(neutral_30_days, int),
            "neutral_90_days": safe_cast(neutral_90_days, int),
            "neutral_12_month": safe_cast(neutral_12_month, int),
            "neutral_lifetime": safe_cast(neutral_lifetime, int),
            "negative_30_days": safe_cast(negative_30_days, int),
            "negative_90_days": safe_cast(negative_90_days, int),
            "negative_12_month": safe_cast(negative_12_month, int),
            "negative_lifetime": safe_cast(negative_lifetime, int),
            "count_30_days": safe_cast(count_30_days, int),
            "count_90_days": safe_cast(count_90_days, int),
            "count_12_month": safe_cast(count_12_month, int),
            "count_lifetime": safe_cast(count_lifetime, int),
            "launched": launched,
            "marketplace_id": "ATVPDKIKX0DER",
            "feedback": json.dumps(feedback_data),
        }
        return data

    def parse_seller_data(self, response, private_label):
        # parse url parameters
        url = response.request.url
        if "proxycrawl" in url:
            url = get_url_from_proxycrawl(url)
            self.crawler.stats.inc_value(AmazonMerchantAutoStats.PROXYCRAWL_SUCCESS.format("seller-about-page"))

        else:
            self.crawler.stats.inc_value(AmazonMerchantAutoStats.CRAWLERA_SUCCESS.format("seller-about-page"))

        data = self.get_seller_data(url, response.body)
        data["private_label"] = private_label

        if data.get("seller_name") is None or data.get("business_name") is None:
            yield get_retry_request(
                request=response.request.copy(), response=response, spider=self, reason="Incomplete seller data"
            )
            return None

        url = f"https://www.amazon.com/s?me={data.get('seller_id')}"

        yield self.build_request(
            url=url,
            callback=self.parse_inventory_info,
            cb_kwargs=data,
        )
