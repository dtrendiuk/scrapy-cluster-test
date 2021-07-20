BOT_NAME = "project"

SPIDER_MODULES = ["project.spiders"]
NEWSPIDER_MODULE = "project.spiders"

REDIS_HOST = "redis"

# General Pipeline
ITEM_PIPELINES = {
    "project.pipelines.ProgressPipeline": 300,
    "project.pipelines.MongoPipeline": 400,
}

RETRY_HTTP_CODES = [429, 503, 520]

DB_HOST = ""
DB_NAME = ""
DB_USER = ""
DB_PASSWORD = ""
