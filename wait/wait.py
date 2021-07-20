#!/usr/bin/env python3
import os
from contextlib import contextmanager


@contextmanager
def cd(newdir):
    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(prevdir)


def deploy_scrapy_project(root_dir="/scrapy_project"):
    with cd(root_dir):
        scrapyd_host = os.getenv("SCRAPYD_HOST")
        os.system(f"wait-for-it -s {scrapyd_host} -- sleep 30 && scrapyd-deploy")


def wait_kafka_brokers(root_dir="/code", cmd="python ./main.py"):
    with cd(root_dir):
        _kafka_hosts = os.getenv("KAFKA_HOST")
        kafka_hosts = _kafka_hosts.split(";")
        param_hosts = "".join([f" -s {host}" for host in kafka_hosts])
        cmd = f"wait-for-it {param_hosts} -- {cmd}"
        os.system(cmd)
