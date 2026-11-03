
BOT_NAME = "books_pipeline"

SPIDER_MODULES = ["books_pipeline.spiders"]
NEWSPIDER_MODULE = "books_pipeline.spiders"

ITEM_PIPELINES = {
    "books_pipeline.pipelines.BooksPipeline": 300,
    "books_pipeline.pipelines.SQLitePipeline": 400,
}

SQLITE_DB_PATH = "books.db"

USER_AGENT = (
    "books_pipeline/1.0 (Enterprise Web Scraping Pipeline; educational project)"
)

FEEDS = {
    "books.json": {
        "format": "json",
        "encoding": "utf-8",
        "indent": 2,
        "overwrite": True,
    },
    "books.csv": {
        "format": "csv",
        "encoding": "utf-8",
        "overwrite": True,
        "fields": ["title", "price", "availability", "product_url", "image_url", "category"],
    },
    "books.xml": {
        "format": "xml",
        "encoding": "utf-8",
        "indent": 2,
        "overwrite": True,
        "item_element": "book",
        "root_element": "books",
    },
}




ROBOTSTXT_OBEY = True

# Politeness 
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 8
DOWNLOAD_DELAY = 0.5
RANDOMIZE_DOWNLOAD_DELAY = True

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.5
AUTOTHROTTLE_MAX_DELAY = 5
AUTOTHROTTLE_TARGET_CONCURRENCY = 4.0

# Reliability
RETRY_ENABLED = True
RETRY_TIMES = 3
DOWNLOAD_TIMEOUT = 30

# Logging 
LOG_ENABLED = True
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
LOG_DATEFORMAT = "%Y-%m-%d %H:%M:%S"

# others
FEED_EXPORT_ENCODING = "utf-8"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"