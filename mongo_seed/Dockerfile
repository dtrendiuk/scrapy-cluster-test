FROM mongo:latest

COPY init.json /init.json
COPY init_autonomous.json /init_autonomous.json
CMD mongoimport --host mongo --db scrapy-cluster --collection proxies --type json --file /init.json --jsonArray && mongoimport --host mongo --db scrapy-cluster --collection amazon_product --type json --file /init_autonomous.json --jsonArray
