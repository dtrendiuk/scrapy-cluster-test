cd /wait
python -c 'import wait; wait.wait_kafka_brokers("./", cmd="sleep 30")'
cd /app
