# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


import copy
import datetime
import json
import os

import numpy as np
import pandas as pd
import requests
from kafka import KafkaProducer
from project.constants import Flag  # type: ignore
from pymongo import UpdateOne
from redis import Redis
from scrapy.utils.project import get_project_settings

from .constants import AmazonMerchantAutoStats
from .db import db
from .spiders.amazon_merchant import AmazonMerchantSpider
from .spiders.amazon_merchant_autonomous import AmazonMerchantAutonomousSpider
from .utils import S3, utc_datetime


class Common:
    def __init__(self):
        self.callback_url = os.getenv("CALLBACK_URL", "http://api/callback")
        self.create_kafka_producer()

    def create_kafka_producer(self):
        _kafka_hosts = os.getenv("KAFKA_HOST")
        kafka_hosts = _kafka_hosts.split(";")
        kafka_ssl = os.getenv("KAFKA_SSL", "True")
        kafka_security_protocol = "PLAINTEXT" if kafka_ssl != "True" else "SSL"

        self.producer = KafkaProducer(
            bootstrap_servers=kafka_hosts,
            security_protocol=kafka_security_protocol,
            value_serializer=lambda m: json.dumps(m).encode("ascii"),
            api_version=(2, 6, 1),
        )

    def process_item(self, item, _):
        self.job_id = item.get("jobid")
        self.project = item.get("project")
        self.spider_name = item.get("spider")
        self.scraped_items_len = item.get("scraped_items_len")

    def _notify_kafka_finished(self, data):
        data["status"] = "finished"

        self.producer.send(f"{data['job_id']}-job", data)
        self.producer.flush()


class ProgressPipeline(Common):
    def __init__(self):
        self.create_kafka_producer()
        self.redis = None

        self.spider = None
        self.project = None
        self.job_id = None

        # Number of Items that has been scraped
        self.scraped_items_len = 0

    def open_spider(self, _):
        settings = get_project_settings()

        redis_host = settings["REDIS_HOST"]
        self.redis = Redis(host=redis_host)  # type: ignore

    def process_item(self, item, spider):
        super().process_item(item, spider)

        if spider._total_expected_len == 0:
            self.producer.send(
                f"{self.job_id}-job",
                {
                    "project": self.project,
                    "spider": self.spider,
                    "job_id": self.job_id,
                    "status": "running",
                    "flag": Flag.DONT_MONITOR_PROGRESS,
                    "total_expected_len": spider._total_expected_len,
                    "scraped_items_len": self.scraped_items_len,
                },
            )
        else:
            self.producer.send(
                f"{self.job_id}-job",
                {
                    "project": self.project,
                    "spider": self.spider,
                    "job_id": self.job_id,
                    "status": "running",
                    "flag": Flag.MONITOR_PROGRESS,
                    "total_expected_len": spider._total_expected_len,
                    "scraped_items_len": self.scraped_items_len,
                },
            )
        self.producer.flush()

        return item


class SellersSpiderPipeline(Common, S3):
    def __init__(self):
        Common.__init__(self)
        S3.__init__(self)

        self.bucket_name = os.getenv("SELLER_BUCKET", "seller-data")
        self.scraped_items_len = None
        self.data = []

    def process_item(self, item, spider):
        super().process_item(item, spider)

        self.data.append(item)
        return item

    @staticmethod
    def make_hyperlink(value):
        return '=HYPERLINK("%s", "%s")' % (value, value)

    @property
    def output(self):
        return self.data

    def output_dataframe(self):
        df = pd.DataFrame(self.output)
        df = df.replace({np.nan: None})

        if df.empty:
            return None, None

        df_2a = df[
            [
                "inventory_link",
                "seller_link",
                "asin",
                "seller_id",
                "seller_name",
                "seller_logo",
                "business_name",
                "address",
                "city",
                "state",
                "zip_code",
                "country",
                "phone",
                "seller_rating",
                "review_ratings",
                "positive_30_days",
                "positive_90_days",
                "positive_12_month",
                "positive_lifetime",
                "neutral_30_days",
                "neutral_90_days",
                "neutral_12_month",
                "neutral_lifetime",
                "negative_30_days",
                "negative_90_days",
                "negative_12_month",
                "negative_lifetime",
                "count_30_days",
                "count_90_days",
                "count_12_month",
                "count_lifetime",
                "launched",
                "marketplace_id",
                "inventory_count",
                "brands",
                "feedback",
                "created_at",
            ]
        ]
        df_2a = df_2a.drop_duplicates(["asin", "seller_id"], ignore_index=True)  # type: ignore
        df_2a["created_at"] = df_2a["created_at"].apply(datetime.datetime.isoformat)  # type: ignore
        df_2a["created_at"] = df_2a["created_at"].astype(str)  # type: ignore

        df_2b = df[
            ["seller_id", "inventory_count", "asins", "seller_link", "inventory_link", "marketplace_id", "created_at"]
        ]
        df_2b = df_2b.drop_duplicates(["seller_id"], ignore_index=True)  # type: ignore

        df_2b["created_at"] = df_2b["created_at"].apply(datetime.datetime.isoformat)  # type: ignore
        df_2b["created_at"] = df_2b["created_at"].astype(str)  # type: ignore

        return df_2a, df_2b

    def _upload_s3(self, df_2a, df_2b):
        dt_now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        df_2a_filename = f"{dt_now}-sellers_2a.csv"
        df_2b_filename = f"{dt_now}-sellers_2b.csv"

        self.upload_dataframe_to_s3(df_2a, df_2a_filename, self.bucket_name)
        self.upload_dataframe_to_s3(df_2b, df_2b_filename, self.bucket_name)

        # Callback
        client = self.create_client()
        df_2a_url = client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self.bucket_name, "Key": df_2a_filename},
        )

        df_2b_url = client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self.bucket_name, "Key": df_2b_filename},
        )

        return df_2a_url, df_2b_url

    def _callback(self, spider, df_2a, df_2b):
        settings = get_project_settings()
        project_name = settings.get("BOT_NAME")

        data = {
            "project": project_name,
            "spider": spider.name,
            "job_id": spider._job,
            "data": {
                "scraped_items_len": self.scraped_items_len,
            },
        }

        self._notify_kafka_finished(data)

        if spider.get_raw and self.output:
            df_2a_raw = df_2a.to_dict(orient="records")  # type: ignore
            df_2b_raw = df_2b.to_dict(orient="records")  # type: ignore

            data["data"]["raw"] = [{"sellers_2a": df_2a_raw, "sellers_2b": df_2b_raw}]
        elif spider.get_raw and not self.output:
            data["data"]["raw"] = [{"sellers_2a": None, "sellers_2b": None}]

        if spider.s3_upload and self.output:
            df_2a_url, df_2b_url = self._upload_s3(df_2a, df_2b)
            data["data"]["s3_links"] = [df_2a_url, df_2b_url]
        elif spider.s3_upload and not self.output:
            data["data"]["s3_links"] = None

        spider.logger.info(f"\n\nresult: {data}\n")
        requests.post(
            self.callback_url,
            json=data,
        )

    def close_spider(self, spider):
        df_2a, df_2b = None, None

        if self.output:
            df_2a, df_2b = self.output_dataframe()

            # Can't rely on per `yield` count. Because of post-processing
            self.scraped_items_len = len(df_2a.index)  # type: ignore

        self._callback(spider, df_2a, df_2b)


class SellerInventoryPipeline(Common, S3):
    def __init__(self):
        Common.__init__(self)
        S3.__init__(self)

        self.bucket_name = os.getenv("SELLER_INVENTORY_BUCKET", "seller-inventory-data")
        self.result = []

    def process_item(self, item, spider):
        super().process_item(item, spider)
        self.result.append(item)
        return item

    @property
    def output(self):
        return self.result

    def output_dataframe(self):
        if self.output:
            df = pd.DataFrame(self.output)[
                [
                    "inventory_link",
                    "seller_link",
                    "seller_id",
                    "asin",
                    "inventory_count",
                    "product_name",
                    "product_url",
                    "current_price",
                    "original_price",
                    "best_seller",
                    "amazon_choice",
                    "reviews_count",
                    "review_stars",
                    "save_and_subscribe",
                    "variation",
                    "category",
                    "marketplace_id",
                    "fba",
                    "fbm",
                    "created_at",
                ]
            ]
            df = df.replace({np.nan: None})
            df["created_at"] = df["created_at"].apply(datetime.datetime.isoformat)  # type: ignore
            df["created_at"] = df["created_at"].astype(str)  # type: ignore
            return df

    def _upload_s3(self, df):
        dt_now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        df_filename = f"seller-inventory-{dt_now}.csv"

        self.upload_dataframe_to_s3(df, df_filename, self.bucket_name)

        client = self.create_client()
        df_url = client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self.bucket_name, "Key": df_filename},
        )

        return df_url

    def _callback(self, spider):
        settings = get_project_settings()
        project_name = settings.get("BOT_NAME")

        df = self.output_dataframe()

        # Get actual lenght
        self.scraped_items_len = len(df.index) if self.output else 0

        data = {
            "project": project_name,
            "spider": spider.name,
            "job_id": spider._job,
            "data": {
                "scraped_items_len": self.scraped_items_len,
                "total_expected_len": spider._total_expected_len,
            },
        }
        self._notify_kafka_finished(data)

        if spider.get_raw and self.output:
            df_raw = df.to_dict(orient="records")  # type: ignore
            data["data"]["raw"] = df_raw
        elif spider.get_raw and not self.output:
            data["data"]["raw"] = None

        if spider.s3_upload and self.output:
            df_url = self._upload_s3(df)
            data["data"]["s3_links"] = [df_url]
        elif spider.s3_upload and not self.output:
            data["data"]["s3_links"] = None

        spider.logger.info(f"\n\nresult: {data}\n")
        requests.post(
            self.callback_url,
            json=data,
        )

    def close_spider(self, spider):
        self._callback(spider)


class MongoPipeline(Common):
    """Save data to MongoDB.
    Note: This pipeline should be a top priority from any other custom pipelines
    """

    def process_item(self, item, spider):
        super().process_item(item, spider)
        item["created_at"] = utc_datetime()

        if AmazonMerchantSpider.name == self.spider_name:
            collection = db[AmazonMerchantSpider.name]
            collection.update_one({"seller_id": item["seller_id"]}, {"$set": item}, upsert=True)
        elif AmazonMerchantAutonomousSpider.name == self.spider_name:
            return item
        else:
            spider.logger.info(f"@mongo_pipeline: spider_name = {self.spider_name}")
            collection = db[self.spider_name]
            collection.insert_one(copy.deepcopy(item))

        return item

    def close_spider(self, spider):
        multi_token = os.getenv("PROXY_MULTI_TOKEN", False)
        if multi_token:
            collection = db["proxies"]
            collection.update_one(
                {"token": spider.proxy_credentials["proxycrawl"]}, {"$set": {"in_used": False}}, upsert=False
            )
            collection.update_one(
                {"token": spider.proxy_credentials["proxycrawl_js"]}, {"$set": {"in_used": False}}, upsert=False
            )
            collection.update_one(
                {"token": spider.proxy_credentials["crawlera"]}, {"$set": {"in_used": False}}, upsert=False
            )


class AmazonMerchantAutonomousPipeline(MongoPipeline):
    def __init__(self):
        super().__init__()

    def process_item(self, item, spider):
        super().process_item(item, spider)
        yield_type = item.get("yield_type")

        todo_asin_bulk_write_operations = []
        todo_seller_id_bulk_operations = []

        # Insert ASINs from inventory to DB
        if yield_type == "from_parse_inventory_info" and item.get("seller_id"):
            asins = item.get("asins")
            if asins:
                for asin in asins:
                    is_isbn = False
                    try:
                        if asin and int(asin[0]):
                            is_isbn = True
                    except ValueError:
                        pass

                    todo_asin_bulk_write_operations.append(
                        UpdateOne(
                            {"asin": asin},
                            {
                                "$setOnInsert": {
                                    "asin": asin,
                                    "is_isbn": is_isbn,
                                    "private_label": item.get("private_label"),
                                    "pending": True,
                                    "last_scraped": None,
                                    "created_at": utc_datetime(),
                                }
                            },
                            upsert=True,
                        )
                    )

            collection = db["amazon_merchant"]
            collection.update_one({"seller_id": item.get("seller_id")}, {"$set": item}, upsert=True)

            todo_seller_id_bulk_operations.append(
                UpdateOne(
                    {"seller_id": item.get("seller_id")},
                    {"$set": {"pending": False, "last_scraped": utc_datetime()}},
                )
            )
            spider.crawler.stats.inc_value(AmazonMerchantAutoStats.INSERTED_SELLER_COUNT)

        elif yield_type == "from_parse_via_asin":
            seller_ids = item.get("seller_ids")
            if seller_ids:
                collection = db["amazon_merchant_autonomous_todo_seller_id"]
                seller_exists = collection.find({"seller_id": {"$in": seller_ids}}, {"seller_id": 1})
                seller_exists_on_todo = [seller["seller_id"] for seller in seller_exists]
                new_seller_ids = list(set(seller_ids) - set(seller_exists_on_todo))

                collection = db["amazon_merchant"]
                seller_exists = collection.find({"seller_id": {"$in": new_seller_ids}}, {"seller_id": 1})
                seller_exists_merchant = [seller["seller_id"] for seller in seller_exists]
                new_seller_ids = list(set(new_seller_ids) - set(seller_exists_merchant))

                if not new_seller_ids:
                    spider.crawler.stats.inc_value(AmazonMerchantAutoStats.ASINS_WITH_ZERO_NEW_SELLERS_COUNT)
                    spider.crawler.stats.inc_value(
                        AmazonMerchantAutoStats.ASINS_WITH_ZERO_NEW_SELLERS_PAGE_COUNT, item.get("num_page", 0)
                    )

                spider.logger.debug(
                    f"ASIN: {item.get('asin')} --\n"
                    f"private_label = {item.get('private_label')}\n"
                    f"received seller_ids = {seller_ids}\n"
                    f"seller_exists_on_todo = {seller_exists_on_todo}\n"
                    f"seller_exists_merchant (seller_ids - seller_exists_on_todo) = {seller_exists_merchant}\n"
                    f"new_seller_ids = {new_seller_ids}"
                )

                for seller_id in new_seller_ids:
                    spider.crawler.stats.inc_value(AmazonMerchantAutoStats.INSERTED_SELLER_ID_COUNT)
                    if item.get("private_label"):
                        spider.crawler.stats.inc_value(AmazonMerchantAutoStats.INSERTED_PRIVATE_LABEL_SELLER_ID_COUNT)
                    else:
                        spider.crawler.stats.inc_value(
                            AmazonMerchantAutoStats.INSERTED_NON_PRIVATE_LABEL_SELLER_ID_COUNT
                        )

                    todo_seller_id_bulk_operations.append(
                        UpdateOne(
                            {"seller_id": seller_id},
                            {
                                "$set": {
                                    "seller_id": seller_id,
                                    "private_label": item.get("private_label"),
                                    "pending": True,
                                    "last_scraped": None,
                                    "created_at": utc_datetime(),
                                }
                            },
                            upsert=True,
                        )
                    )
            else:
                spider.crawler.stats.inc_value(AmazonMerchantAutoStats.ASINS_WITH_ZERO_NEW_SELLERS_COUNT)
                spider.crawler.stats.inc_value(
                    AmazonMerchantAutoStats.ASINS_WITH_ZERO_NEW_SELLERS_PAGE_COUNT, item.get("num_page", 0)
                )

            todo_asin_bulk_write_operations.append(
                UpdateOne(
                    {"asin": item.get("asin")},
                    {
                        "$set": {
                            "asin": item.get("asin"),
                            "num_offers": item.get("num_offers"),
                            "num_unique_sellers": item.get("num_unique_sellers"),
                            "private_label": item.get("private_label"),
                            "pending": False,
                            "last_scraped": utc_datetime(),
                            "created_at": utc_datetime(),
                        }
                    },
                )
            )
        elif yield_type == "parse_next_inventory_page" and item.get("asins"):
            asins = item.get("asins")
            for asin in asins:
                is_isbn = False
                try:
                    if asin and int(asin[0]):
                        is_isbn = True
                except ValueError:
                    pass

                todo_asin_bulk_write_operations.append(
                    UpdateOne(
                        {"asin": asin},
                        {
                            "$setOnInsert": {
                                "asin": asin,
                                "is_isbn": is_isbn,
                                "private_label": item.get("private_label"),
                                "pending": True,
                                "last_scraped": None,
                                "created_at": utc_datetime(),
                            }
                        },
                        upsert=True,
                    )
                )

        if todo_asin_bulk_write_operations:
            collection = db["amazon_product"]
            collection.bulk_write(todo_asin_bulk_write_operations, ordered=False)

        if todo_seller_id_bulk_operations:
            collection = db["amazon_merchant_autonomous_todo_seller_id"]
            collection.bulk_write(todo_seller_id_bulk_operations, ordered=False)

        return item
