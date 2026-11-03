import logging
from typing import Dict, List, Optional, Tuple

from scrapy.http import Response

from books_pipeline.items import BooksPipelineItem

logger = logging.getLogger(__name__)


class CategoryParser:
    """Extract book categories from the homepage sidebar."""

    LINK_SELECTOR = "div.side_categories ul.nav-list > li > ul > li > a"

    def parse(self, response: Response) -> List[Dict[str, str]]:
        """Return category names and absolute URLs."""
        categories = []
        for link in response.css(self.LINK_SELECTOR):
            name = " ".join(link.css("::text").get(default="").split())
            href = link.attrib.get("href")
            if not name or not href:
                logger.warning("Skipping malformed category link: %s", link.get())
                continue
            categories.append({"name": name, "url": response.urljoin(href)})
        return categories


class BookListParser:
    """Extract book URLs and the next page link from a category page."""

    BOOK_LINK_SELECTOR = "article.product_pod h3 a::attr(href)"
    NEXT_PAGE_SELECTOR = "li.next a::attr(href)"

    def parse(self, response: Response) -> Tuple[List[str], Optional[str]]:
        """Return absolute book URLs and the next page URL (or None)."""
        book_urls = [
            response.urljoin(href)
            for href in response.css(self.BOOK_LINK_SELECTOR).getall()
        ]
        next_href = response.css(self.NEXT_PAGE_SELECTOR).get()
        next_url = response.urljoin(next_href) if next_href else None
        return book_urls, next_url


class BookDetailParser:
    """Build a book item from a book detail page."""

    TITLE_SELECTOR = "div.product_main h1::text"
    PRICE_SELECTOR = "div.product_main p.price_color::text"
    AVAILABILITY_SELECTOR = "div.product_main p.availability::text"
    IMAGE_SELECTOR = "div.item.active img::attr(src)"

    def parse(self, response: Response, category: str) -> Optional[BooksPipelineItem]:
        """Return the raw item, or None if the page has no title."""
        title = response.css(self.TITLE_SELECTOR).get()
        if not title:
            logger.error("No title found on %s; skipping book.", response.url)
            return None

        image_href = response.css(self.IMAGE_SELECTOR).get()

        item = BooksPipelineItem()
        item["title"] = title
        item["price"] = response.css(self.PRICE_SELECTOR).get()
        item["availability"] = " ".join(
            response.css(self.AVAILABILITY_SELECTOR).getall()
        )
        item["product_url"] = response.url
        item["image_url"] = response.urljoin(image_href) if image_href else None
        item["category"] = category
        return item