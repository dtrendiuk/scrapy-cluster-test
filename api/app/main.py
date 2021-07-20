import hashlib
import json
import logging
import math
import os
import sys
import urllib
import uuid
from typing import Optional, Tuple

import pymongo
import requests
import sentry_sdk
from app.crypt import CryptID
from bson import ObjectId
from fastapi import FastAPI, HTTPException
from jwt import ExpiredSignatureError
from kafka import KafkaProducer
from pydantic import BaseModel
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from starlette.requests import Request

app = FastAPI()
secret = bytes(os.getenv("SECRET", "changeme"), encoding="utf8")  # type: ignore
secret = hashlib.sha256(secret).digest()

sentry_dsn = os.getenv("SENTRY_DSN", None)
sentry_enabled = os.getenv("SENTRY_ENABLED", "false")
sentry_environment = os.getenv("SENTRY_ENVIRONMENT", "dev")

_kafka_hosts = os.getenv("KAFKA_HOST")
kafka_hosts = _kafka_hosts.split(";")
kafka_ssl = os.getenv("KAFKA_SSL", "True")
kafka_security_protocol = "PLAINTEXT" if kafka_ssl != "True" else "SSL"

if sentry_enabled.lower() == "true":
    sentry_sdk.init(dsn=sentry_dsn, environment=sentry_environment)
    SentryAsgiMiddleware(app)

logging.config.fileConfig("logging.conf", disable_existing_loggers=False)  # type: ignore
logger = logging.getLogger(__name__)

producer = KafkaProducer(
    bootstrap_servers=kafka_hosts,
    security_protocol=kafka_security_protocol,
    value_serializer=lambda m: json.dumps(m).encode("ascii"),
    api_version=(2, 6, 1),
)

mongo_host = os.getenv("MONGODB", "mongodb://mongo")
db_client = pymongo.MongoClient(mongo_host)
db = db_client["scrapy-cluster"]
crypt = CryptID(secret)


class Schedule(BaseModel):
    project: str
    spider: str
    total_expected_len: Optional[int] = 0
    data: Optional[dict]


class Callback(BaseModel):
    project: str
    spider: str
    job_id: str
    data: Optional[dict]


@app.post("/schedule-job")
async def schedule_job(job: Schedule):
    scrapyd_host = os.getenv("SCRAPYD_HOST", "scrapyd:6800")
    scrapyd_username = os.getenv("SCRAPYD_USERNAME", "debug")
    scrapyd_password = os.getenv("SCRAPYD_PASSWORD", "debug")

    url = f"http://{scrapyd_host}/listspiders.json?project=project"
    resp = requests.get(url, auth=(scrapyd_username, scrapyd_password))
    valid_spiders = resp.json()["spiders"]
    if job.spider not in valid_spiders:
        return {"success": False, "message": "Not a valid spider"}

    job_id = uuid.uuid4().hex
    producer.send(
        "todo_jobs",
        {
            "job_id": job_id,
            "project": job.project,
            "spider": job.spider,
            "total_expected_len": job.total_expected_len,
            "data": job.data,
        },
    )
    producer.flush()
    return {"success": True, "job_id": job_id}


@app.get("/seller-database")
def seller_database(
    request: Request,
    per_page: int = None,
    page: int = None,
    ordering: Optional[str] = None,
    seller_ids: Optional[str] = None,
    seller_name: Optional[str] = None,
    business_name: Optional[str] = None,
    asins: Optional[str] = None,
    seller_link: Optional[str] = None,
    state: Optional[str] = None,
    marketplace_id: Optional[str] = None,
    brands: Optional[str] = None,
    country: Optional[str] = None,
    launched: Optional[str] = None,
    seller_rating: Optional[float] = None,
    seller_rating_min: Optional[float] = None,
    seller_rating_max: Optional[float] = None,
    number_brands: Optional[int] = None,
    number_brands_min: Optional[int] = None,
    number_brands_max: Optional[int] = None,
    review_ratings: Optional[int] = None,
    review_ratings_min: Optional[int] = None,
    review_ratings_max: Optional[int] = None,
    inventory_count: Optional[int] = None,
    inventory_count_min: Optional[int] = None,
    inventory_count_max: Optional[int] = None,
    count_30_days: Optional[int] = None,
    count_30_days_min: Optional[int] = None,
    count_30_days_max: Optional[int] = None,
    count_12_month: Optional[int] = None,
    count_12_month_min: Optional[int] = None,
    count_12_month_max: Optional[int] = None,
    count_90_days: Optional[int] = None,
    count_90_days_min: Optional[int] = None,
    count_90_days_max: Optional[int] = None,
    count_lifetime: Optional[int] = None,
    count_lifetime_min: Optional[int] = None,
    count_lifetime_max: Optional[int] = None,
    positive_30_days: Optional[int] = None,
    positive_30_days_min: Optional[int] = None,
    positive_30_days_max: Optional[int] = None,
    positive_90_days: Optional[int] = None,
    positive_90_days_min: Optional[int] = None,
    positive_90_days_max: Optional[int] = None,
    positive_12_month: Optional[int] = None,
    positive_12_month_min: Optional[int] = None,
    positive_12_month_max: Optional[int] = None,
    positive_lifetime: Optional[int] = None,
    positive_lifetime_min: Optional[int] = None,
    positive_lifetime_max: Optional[int] = None,
    neutral_30_days: Optional[int] = None,
    neutral_30_days_min: Optional[int] = None,
    neutral_30_days_max: Optional[int] = None,
    neutral_90_days: Optional[int] = None,
    neutral_90_days_min: Optional[int] = None,
    neutral_90_days_max: Optional[int] = None,
    neutral_12_month: Optional[int] = None,
    neutral_12_month_min: Optional[int] = None,
    neutral_12_month_max: Optional[int] = None,
    neutral_lifetime: Optional[int] = None,
    neutral_lifetime_min: Optional[int] = None,
    neutral_lifetime_max: Optional[int] = None,
    negative_30_days: Optional[int] = None,
    negative_30_days_min: Optional[int] = None,
    negative_30_days_max: Optional[int] = None,
    negative_90_days: Optional[int] = None,
    negative_90_days_min: Optional[int] = None,
    negative_90_days_max: Optional[int] = None,
    negative_12_month: Optional[int] = None,
    negative_12_month_min: Optional[int] = None,
    negative_12_month_max: Optional[int] = None,
    negative_lifetime: Optional[int] = None,
    negative_lifetime_min: Optional[int] = None,
    negative_lifetime_max: Optional[int] = None,
):
    """Main function for fetching live merchants from MongoDB."""
    if not per_page or per_page <= 0:
        raise HTTPException(status_code=400, detail="Invalid per_page value")

    if not page or page <= 0:
        raise HTTPException(status_code=400, detail="Invalid page value")

    def _get_next_prev_url(req: Request, max_pages: int, current_page: int) -> Tuple[Optional[str], Optional[str]]:
        before_url = req.url.include_query_params(page=current_page - 1) if 0 < current_page - 1 < max_pages else None
        after_url = req.url.include_query_params(page=current_page + 1) if 2 <= current_page + 1 <= max_pages else None
        return before_url.query if before_url else None, after_url.query if after_url else None

    collection = db["amazon_merchant"]

    # sorting helper
    valid_merchant_fields = [
        "seller_id",
        "address",
        "asin",
        "asins",
        "brands",
        "business_name",
        "city",
        "count_12_month",
        "count_30_days",
        "count_90_days",
        "count_lifetime",
        "country",
        "feedback",
        "inventory_count",
        "inventory_link",
        "launched",
        "marketplace_id",
        "negative_12_month",
        "negative_30_days",
        "negative_90_days",
        "negative_lifetime",
        "phone",
        "positive_12_month",
        "positive_30_days",
        "positive_90_days",
        "positive_lifetime",
        "neutral_12_month",
        "neutral_30_days",
        "neutral_90_days",
        "neutral_lifetime",
        "review_ratings",
        "seller_link",
        "seller_name",
        "seller_rating",
        "state",
        "zip_code",
        "is_isbn",
        "private_label",
        "seller_logo",
        "id",
    ]
    # sorting functions
    sort = {}
    if ordering:
        sort["$sort"] = {}
        orderings = ordering.split(",")
        for field in orderings:
            direction = pymongo.ASCENDING
            if field[0] == "-":
                direction = pymongo.DESCENDING
                field = field[1:]

            if field not in valid_merchant_fields:
                raise HTTPException(status_code=404, detail="Invalid ordering value")

            if field == "id":
                field = "_id"

            # consistent sorting as per https://docs.mongodb.com/manual/reference/operator/aggregation/sort/
            sort["$sort"].setdefault(field, direction)

    # filtering functions
    filter_helper = [
        {"base": seller_rating, "min": seller_rating_min, "max": seller_rating_max, "value_key": "seller_rating"},
        {"base": review_ratings, "min": review_ratings_min, "max": review_ratings_max, "value_key": "review_ratings"},
        {"base": count_30_days, "min": count_30_days_min, "max": count_30_days_max, "value_key": "count_30_days"},
        {"base": count_90_days, "min": count_90_days_min, "max": count_90_days_max, "value_key": "count_90_days"},
        {"base": count_12_month, "min": count_12_month_min, "max": count_12_month_max, "value_key": "count_12_month"},
        {"base": count_lifetime, "min": count_lifetime_min, "max": count_lifetime_max, "value_key": "count_lifetime"},
        {"base": number_brands, "min": number_brands_min, "max": number_brands_max, "value_key": "brands"},
        {
            "base": inventory_count,
            "min": inventory_count_min,
            "max": inventory_count_max,
            "value_key": "inventory_count",
        },
        {
            "base": positive_30_days,
            "min": positive_30_days_min,
            "max": positive_30_days_max,
            "value_key": "positive_30_days",
        },
        {
            "base": positive_90_days,
            "min": positive_90_days_min,
            "max": positive_90_days_max,
            "value_key": "positive_90_days",
        },
        {
            "base": positive_12_month,
            "min": positive_12_month_min,
            "max": positive_12_month_max,
            "value_key": "positive_12_month",
        },
        {
            "base": positive_lifetime,
            "min": positive_lifetime_min,
            "max": positive_lifetime_max,
            "value_key": "positive_lifetime",
        },
        {
            "base": neutral_30_days,
            "min": neutral_30_days_min,
            "max": neutral_30_days_max,
            "value_key": "neutral_30_days",
        },
        {
            "base": neutral_90_days,
            "min": neutral_90_days_min,
            "max": neutral_90_days_max,
            "value_key": "neutral_90_days",
        },
        {
            "base": neutral_12_month,
            "min": neutral_12_month_min,
            "max": neutral_12_month_max,
            "value_key": "neutral_12_month",
        },
        {
            "base": neutral_lifetime,
            "min": neutral_lifetime_min,
            "max": neutral_lifetime_max,
            "value_key": "neutral_lifetime",
        },
        {
            "base": negative_30_days,
            "min": negative_30_days_min,
            "max": negative_30_days_max,
            "value_key": "negative_30_days",
        },
        {
            "base": negative_90_days,
            "min": negative_90_days_min,
            "max": negative_90_days_max,
            "value_key": "negative_90_days",
        },
        {
            "base": negative_12_month,
            "min": negative_12_month_min,
            "max": negative_12_month_max,
            "value_key": "negative_12_month",
        },
        {
            "base": negative_lifetime,
            "min": negative_lifetime_min,
            "max": negative_lifetime_max,
            "value_key": "negative_lifetime",
        },
    ]
    filter_query = {"$match": {}}

    for filters in filter_helper:
        if filters["base"] is not None:
            filter_query["$match"][filters["value_key"]] = filters["base"]
        elif filters["value_key"] == "brands":
            if filters["base"] is not None:
                filter_query["$match"][filters["value_key"]] = {"$ne": None}
                filter_query["$match"]["$expr"] = {
                    "$and": [
                        {"$ne": ["$brands", None]},
                        {"$eq": [{"$size": "$brands"}, filters["base"]]},
                    ]
                }
            else:
                filter_query["$match"][filters["value_key"]] = {"$ne": None}
                filter_query["$match"]["$expr"] = {
                    "$and": [
                        {"$gte": [{"$size": "$brands"}, filters["min"] if filters["min"] is not None else 0]},
                        {"$lte": [{"$size": "$brands"}, filters["max"] if filters["max"] is not None else sys.maxsize]},
                    ]
                }
        else:
            if any([filters["min"] is not None, filters["max"] is not None]):
                filtering_body = {"$ne": None}
                if filters["min"] is not None:
                    filtering_body.setdefault("$gte", filters["min"] if filters["min"] is not None else 0)
                if filters["max"] is not None:
                    filtering_body.setdefault("$lte", filters["max"] if filters["max"] is not None else sys.maxsize)

                filter_query["$match"][filters["value_key"]] = filtering_body

    # search functions
    search = {}
    search_merchant_fields = {
        "seller_ids": seller_ids,
        "seller_name": seller_name,
        "asins": asins,
        "seller_link": seller_link,
        "state": state,
        "marketplace_id": marketplace_id,
        "brands": brands,
        "country": country,
        "launched": launched,
        "business_name": business_name,
    }
    for search_field, search_value in search_merchant_fields.items():
        if search_value is not None:
            # blocking for dangerous nosql (temporary fix)
            if "$where" in search_value:
                raise HTTPException(status_code=500, detail="Error processing request")

            if search_field == "asins":
                values = []
                value_list = search_value.split(",")
                for value in value_list:
                    values.append({"asin": value.strip()})
                    values.append({"asins": value.strip()})

                if "$match" in search:
                    search["$match"].update({"$or": values})
                else:
                    search["$match"] = {"$or": values}
            elif search_field in ("seller_ids"):
                values = []
                value_list = search_value.split(",")
                for value in value_list:
                    values.append(
                        {
                            "seller_id": {
                                "$regex": value.strip(),
                                "$options": "i",
                            }
                        }
                    )

                if "$match" in search:
                    search["$match"].update({"$or": values})
                else:
                    search["$match"] = {"$or": values}
            elif search_field in ("state"):
                if "$match" in search:
                    search["$match"].update({search_field: search_value})
                else:
                    search["$match"] = {search_field: search_value}
            elif search_field in ("brands"):
                values = []
                value_list = search_value.split(",")
                for value in value_list:
                    values.append(
                        {
                            search_field: {
                                "$regex": value.strip(),
                                "$options": "i",
                            }
                        }
                    )

                if "$match" in search:
                    search["$match"].update({"$or": values})
                else:
                    search["$match"] = {"$or": values}
            else:
                if "$match" in search:
                    search["$match"].update(
                        {
                            search_field: {
                                "$regex": search_value,
                                "$options": "i",
                            }
                        }
                    )
                else:
                    search["$match"] = {
                        search_field: {
                            "$regex": search_value,
                            "$options": "i",
                        }
                    }

    if number_brands is not None:
        pass

    excluded_fields = [
        "_id",
        "jobid",
        "project",
        "spider",
        "total_expected_len",
        "scraped_items_len",
        "brand_matched",
        "checked_emails",
        "confirmed_email",
        "confirmed_name",
        "confirmed_phone",
        "contacted",
        "contacted_date",
        "fba_percent_n5p",
        "fba_percent_p5p",
        "growth_L180D",
        "growth_L90D",
        "growth_count_L180D",
        "growth_month",
        "growth_month_count",
        "growth_year",
        "legal_name",
        "marketplace",
        "qualified_brands",
        "sales_estimate_n5p",
        "sales_estimate_p5p",
        "top_asins_count",
        "top_brands_count",
        "total_brands",
        "latitude",
        "longitude",
    ]

    id_conversion = {"$addFields": {"id": {"$toString": "$_id"}}}

    # pipeline stages - ID conversion to str, filtering, sorting, search, per_page_limit, page_skip, excluded_fields
    pipeline = []

    if filter_query["$match"]:
        pipeline.append(filter_query)

    if search:
        pipeline.append(search)

    # query total number of documents, using seller_id index
    count_pipeline = pipeline.copy()
    count_pipeline.append({"$group": {"_id": "$seller_id", "count": {"$sum": 1}}})
    count_pipeline.append({"$count": "count"})
    total_sellers = collection.aggregate(pipeline=count_pipeline, allowDiskUse=True)
    total_sellers = [total_seller for total_seller in total_sellers]
    total_sellers = total_sellers[0]["count"] if len(total_sellers) > 0 else 0

    if sort:
        pipeline.append(sort)

    pipeline.append({"$skip": (page - 1) * per_page})
    pipeline.append({"$limit": per_page})
    pipeline.append(id_conversion)
    pipeline.append({"$unset": excluded_fields})

    # https://docs.mongodb.com/manual/core/aggregation-pipeline-limits/#std-label-agg-memory-restrictions
    sellers = collection.aggregate(pipeline=pipeline, allowDiskUse=True)
    sellers = [seller for seller in sellers]
    count = len(sellers)
    total_pages = math.ceil(total_sellers / per_page) if count > 0 else 1
    prev_url, next_url = _get_next_prev_url(request, total_pages, page)

    results = {
        "count": total_sellers,
        "current_page": page,
        "next": next_url,
        "per_page": per_page,
        "previous": prev_url,
        "results": sellers,
        "total_pages": total_pages,
    }

    return results


@app.get("/seller-maps")
def seller_maps(
    max_count: int = None,
    state: Optional[str] = None,
    marketplace_id: Optional[str] = None,
    zip_code: Optional[str] = None,
    country: Optional[str] = None,
):
    """Main function for fetching live merchants from MongoDB."""
    if not max_count or max_count <= 0:
        raise HTTPException(status_code=400, detail="Invalid max_count value")

    collection = db["amazon_merchant"]

    search = {"$match": {"latitude": {"$ne": None}}}
    country_value = "US" if state or zip_code else None
    if country:
        country_value = country
    search_merchant_fields = {
        "state": state,
        "marketplace_id": marketplace_id,
        "zip_code": zip_code,
        "country": country_value,
    }

    for search_field, search_value in search_merchant_fields.items():
        if search_value is not None:
            # blocking for dangerous nosql (temporary fix)
            if "$where" in search_value:
                raise HTTPException(status_code=500, detail="Error processing request")
            if search_field in ("state", "country"):
                search["$match"].update(
                    {
                        search_field: {
                            "$regex": f"^{search_value}$",
                            "$options": "i",
                        }
                    }
                )
            elif search_field in ("zip_code"):
                search["$match"].update(
                    {
                        search_field: {
                            "$regex": f"^{search_value}.*",
                            "$options": "i",
                        }
                    }
                )
            else:
                search["$match"].update(
                    {
                        search_field: {
                            "$regex": search_value,
                            "$options": "i",
                        }
                    }
                )

    rows = collection.aggregate(
        [
            search,
            {"$addFields": {"id": {"$toString": "$_id"}}},
            {"$project": {"_id": 0, "id": 1, "latitude": 1, "longitude": 1}},
            {"$limit": max_count},
        ],
        allowDiskUse=True,
    )

    result = []

    for row in rows:
        row["id"] = urllib.parse.quote(crypt.encryt(row["id"]))
        result.append(row)

    return result


@app.get("/seller")
def seller(
    id: str = None,
):
    """Main function for fetching live merchants from MongoDB."""
    if not id:
        raise HTTPException(status_code=400, detail="Invalid id value")

    try:
        id = crypt.decrypt(id)
    except ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Your Session Has Expired, Please Refresh and Try Again")

    collection = db["amazon_merchant"]

    results = collection.aggregate(
        [
            {"$match": {"_id": ObjectId(id)}},
            {
                "$project": {
                    "_id": 0,
                    "seller_id": 1,
                    "business_name": 1,
                    "city": 1,
                    "seller_link": 1,
                    "seller_name": 1,
                    "state": 1,
                    "zip_code": 1,
                    "country": 1,
                    "inventory_count": 1,
                    "brands": 1,
                }
            },
        ],
        allowDiskUse=True,
    )
    results = [result for result in results]
    return results
