import json
import os
import time
from logging import config, getLogger

import pymongo
import requests
import sentry_sdk
from kafka import KafkaConsumer

_kafka_hosts = os.getenv("KAFKA_HOST")
kafka_hosts = _kafka_hosts.split(";")
kafka_ssl = os.getenv("KAFKA_SSL", "True")
kafka_security_protocol = "PLAINTEXT" if kafka_ssl != "True" else "SSL"

scrapyd_host = os.getenv("SCRAPYD_HOST")
scrapyd_username = os.getenv("SCRAPYD_USERNAME")
scrapyd_password = os.getenv("SCRAPYD_PASSWORD")

config.fileConfig("logging.conf", disable_existing_loggers=False)  # type: ignore
logger = getLogger(__name__)


def schedule_job(project, spider, job_id, total_expected_len, data, **_):
    mongo_host = os.getenv("MONGODB", "mongodb://mongo")
    db_client = pymongo.MongoClient(mongo_host)
    db = db_client["scrapy-cluster"]

    collection = db["proxies"]
    crawlera = None
    proxycrawl = None
    proxycrawl_js = None

    proxy_sleep_retry = int(os.getenv("PROXY_SLEEP_RETRY", 3))

    while crawlera is None or proxycrawl is None or proxycrawl_js is None:
        proxies = collection.find({"in_used": False})
        for proxy in proxies:
            if proxy["provider"] == "crawlera":
                crawlera = proxy
            elif proxy["provider"] == "proxycrawl":
                proxycrawl = proxy
            elif proxy["provider"] == "proxycrawl_js":
                proxycrawl_js = proxy

        if crawlera and proxycrawl and proxycrawl_js:
            break

        logger.info("Waiting for proxy token availability...")
        time.sleep(proxy_sleep_retry)

    multi_token = os.getenv("PROXY_MULTI_TOKEN", False)
    if multi_token:
        collection.update_one({"_id": proxycrawl["_id"]}, {"$set": {"in_used": True}}, upsert=False)
        collection.update_one({"_id": proxycrawl_js["_id"]}, {"$set": {"in_used": True}}, upsert=False)
        collection.update_one({"_id": crawlera["_id"]}, {"$set": {"in_used": True}}, upsert=False)

    proxy = {"crawlera": crawlera["token"], "proxycrawl": proxycrawl["token"], "proxycrawl_js": proxycrawl_js["token"]}

    post_data = {
        "project": project,
        "spider": spider,
        "jobid": job_id,
        "total_expected_len": total_expected_len,
        "proxy": json.dumps(proxy),
        "data": json.dumps(data),
    }

    resp = requests.post(
        f"http://{scrapyd_host}/schedule.json",
        data=post_data,
        auth=(scrapyd_username, scrapyd_password),
    )

    logger.info(resp.json())
    db_client.close()


def start():
    logger.info("Service has started successfully")
    sentry_dsn = os.getenv("SENTRY_DSN", None)
    sentry_enabled = os.getenv("SENTRY_ENABLED", "false")

    if sentry_enabled.lower() == "true":
        sentry_sdk.init(dsn=sentry_dsn)

    consumer = KafkaConsumer(
        "todo_jobs",
        "done_jobs",
        bootstrap_servers=kafka_hosts,
        security_protocol=kafka_security_protocol,
        value_deserializer=lambda m: json.loads(m.decode("ascii")),
    )

    for msg in consumer:
        topic = msg.topic
        value = msg.value
        logger.info("job received")

        if topic == "todo_jobs":
            schedule_job(**value)


if __name__ == "__main__":
    start()
