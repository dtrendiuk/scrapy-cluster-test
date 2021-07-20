import os

import pymongo


class DB:
    def __init__(self):
        self.connect_db()

    def connect_db(self):
        mongo_host = os.getenv("MONGODB", "mongodb://mongo")
        self.db_client = pymongo.MongoClient(mongo_host)
        self.db = self.db_client["scrapy-cluster"]


db = DB().db
