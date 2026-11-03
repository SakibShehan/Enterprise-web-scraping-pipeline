import re
import unicodedata

from itemadapter import ItemAdapter
from scrapy.exceptions import DropItem


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