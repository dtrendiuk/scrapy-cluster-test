#!/bin/bash
cd /wait
python3 -c "import wait; wait.deploy_scrapy_project()"
python3 -c "import wait; wait.wait_kafka_brokers()"
