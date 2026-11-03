import re
import unicodedata

from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem


import sqlite3



class BooksPipeline:
    # Clean and normalize book items

    TEXT_FIELDS = ("title", "category")
    URL_FIELDS = ("product_url", "image_url")
    PRICE_CLEANER = re.compile(r"[^\d.]")

    def process_item(self, item, spider):
        # Clean all fields, drop the item if title or price is unusable
        adapter = ItemAdapter(item)

        for field in self.TEXT_FIELDS:
            adapter[field] = self.normalize_text(adapter.get(field))

        for field in self.URL_FIELDS:
            adapter[field] = self.normalize_text(adapter.get(field))

        if not adapter.get("title"):
            raise DropItem("Missing title")

        adapter["price"] = self.parse_price(adapter.get("price"))
        if adapter["price"] is None:
            raise DropItem(f"Invalid price for: {adapter['title']}")

        adapter["availability"] = self.parse_availability(adapter.get("availability"))

        spider.logger.debug("Cleaned item: %s", adapter["title"])
        return item

    def normalize_text(self, value):
        # Normalize unicode and collapse extra whitespace
        if value is None:
            return ""
        return " ".join(unicodedata.normalize("NFKC", str(value)).split())

    def parse_price(self, value):
        # Remove currency symbols and convert to float
        cleaned = self.PRICE_CLEANER.sub("", str(value or "").replace(",", ""))
        try:
            return float(cleaned)
        except ValueError:
            return None

    def parse_availability(self, value) -> bool:
        # "In stock" -> True, anything else -> False
        return self.normalize_text(value).lower().startswith("in stock")


# Table for store scraped book data in SQLite

class SQLitePipeline:
    # Store cleaned book items in SQLite

    CREATE_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            price REAL NOT NULL,
            availability INTEGER NOT NULL,
            product_url TEXT NOT NULL,
            image_url TEXT,
            category TEXT NOT NULL
        )
    """
    INSERT_SQL = """
        INSERT INTO books (title, price, availability, product_url, image_url, category)
        VALUES (?, ?, ?, ?, ?, ?)
    """

    def __init__(self, db_path):
        self.db_path = db_path
        self.connection = None

    @classmethod
    def from_crawler(cls, crawler):
        # Read the database path from settings
        return cls(crawler.settings.get("SQLITE_DB_PATH", "books.db"))

    def open_spider(self, spider):
        # Open the connection, create the table, clear rows from the last crawl
        self.connection = sqlite3.connect(self.db_path)
        self.connection.execute(self.CREATE_TABLE_SQL)
        self.connection.execute("DELETE FROM books")
        self.connection.commit()
        spider.logger.info("SQLite database ready: %s", self.db_path)

    def close_spider(self, spider):
        # Commit and close the connection
        if self.connection:
            self.connection.commit()
            self.connection.close()
            spider.logger.info("SQLite database closed: %s", self.db_path)

    def process_item(self, item, spider):
        # Insert one item with a parameterized query
        adapter = ItemAdapter(item)
        try:
            self.connection.execute(
                self.INSERT_SQL,
                (
                    adapter["title"],
                    adapter["price"],
                    int(adapter["availability"]),
                    adapter["product_url"],
                    adapter["image_url"],
                    adapter["category"],
                ),
            )
        except sqlite3.Error as error:
            spider.logger.error("SQLite insert failed for %s: %s", adapter["title"], error)
            raise DropItem(f"Database insert failed: {error}")
        return item