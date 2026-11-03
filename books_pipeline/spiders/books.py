import random
from typing import Dict, List, Optional

import scrapy
from scrapy.http import Response

from books_pipeline.items import BooksPipelineItem


class BooksSpider(scrapy.Spider):
    # Crawl Books to Scrape starting from its homepage

    name = "books"
    allowed_domains = ["books.toscrape.com"]
    start_url = "https://books.toscrape.com/index.html"

    CATEGORY_SAMPLE_SIZE = 7
    BOOKS_PER_CATEGORY = 5
    CATEGORY_LINK_SELECTOR = "div.side_categories ul.nav-list > li > ul > li > a"
    BOOK_LINK_SELECTOR = "article.product_pod h3 a::attr(href)"
    NEXT_PAGE_SELECTOR = "li.next a::attr(href)"
    TITLE_SELECTOR = "div.product_main h1::text"
    PRICE_SELECTOR = "div.product_main p.price_color::text"
    AVAILABILITY_SELECTOR = "div.product_main p.availability::text"
    IMAGE_SELECTOR = "div.item.active img::attr(src)"

    def __init__(self, seed: Optional[str] = None, *args, **kwargs):
        # Optional seed makes random selection repeatable
        super().__init__(*args, **kwargs)
        self.seed = seed
        self.rng = random.Random(seed)
        self.selected_categories: List[Dict[str, str]] = []

    async def start(self):
        # Send the first request to the homepage
        self.logger.info("Starting crawl at %s", self.start_url)
        yield scrapy.Request(
            self.start_url,
            callback=self.parse,
            errback=self.handle_error,
        )

    def parse(self, response: Response):
        # Discover all categories, select a random sample, crawl each one
        categories = self.extract_categories(response)

        if not categories:
            self.logger.error(
                "No categories found on %s; the page layout may have changed.",
                response.url,
            )
            return

        self.selected_categories = self.select_categories(categories)
        self.logger.info(
            "Discovered %d categories; randomly selected %d",
            len(categories),
            len(self.selected_categories),
        )

        for category in self.selected_categories:
            self.logger.info(
                "Selected category: %s -> %s", category["name"], category["url"]
            )
            yield scrapy.Request(
                category["url"],
                callback=self.parse_category,
                errback=self.handle_error,
                cb_kwargs={"category": category["name"], "book_urls": [], "pages": 0},
            )

    def parse_category(
        self, response: Response, category: str, book_urls: List[str], pages: int
    ):
        # Collect book URLs from this page, then follow the next page if any
        pages += 1
        page_urls = [
            response.urljoin(href)
            for href in response.css(self.BOOK_LINK_SELECTOR).getall()
        ]
        book_urls = book_urls + page_urls
        self.logger.debug(
            "Category %s page %d: %d books", category, pages, len(page_urls)
        )

        next_href = response.css(self.NEXT_PAGE_SELECTOR).get()
        if next_href:
            yield scrapy.Request(
                response.urljoin(next_href),
                callback=self.parse_category,
                errback=self.handle_error,
                cb_kwargs={"category": category, "book_urls": book_urls, "pages": pages},
            )
            return

        self.logger.info(
            "Category %s: collected %d books across %d page(s)",
            category,
            len(book_urls),
            pages,
        )

        # Last page reached, so sample books and request their detail pages
        selected_urls = self.select_books(book_urls)
        self.logger.info(
            "Category %s: selected %d of %d books",
            category,
            len(selected_urls),
            len(book_urls),
        )
        for url in selected_urls:
            yield scrapy.Request(
                url,
                callback=self.parse_book,
                errback=self.handle_error,
                cb_kwargs={"category": category},
            )

    def parse_book(self, response: Response, category: str):
        # Extract the six fields from a book detail page
        title = response.css(self.TITLE_SELECTOR).get()
        if not title:
            self.logger.error("No title found on %s; skipping book.", response.url)
            return

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

        self.logger.debug("Extracted book [%s]: %s", category, title)
        yield item

    def extract_categories(self, response: Response) -> List[Dict[str, str]]:
        # Extract category names and absolute URLs from the sidebar
        categories = []
        for link in response.css(self.CATEGORY_LINK_SELECTOR):
            name = " ".join(link.css("::text").get(default="").split())
            href = link.attrib.get("href")
            if not name or not href:
                self.logger.warning("Skipping malformed category link: %s", link.get())
                continue
            categories.append({"name": name, "url": response.urljoin(href)})
        return categories

    def select_categories(
        self, categories: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        # Pick distinct random categories, or all if fewer than the sample size
        sample_size = min(self.CATEGORY_SAMPLE_SIZE, len(categories))
        if sample_size < self.CATEGORY_SAMPLE_SIZE:
            self.logger.warning(
                "Only %d categories available; selecting all of them.",
                len(categories),
            )
        return self.rng.sample(categories, sample_size)

    def select_books(self, book_urls: List[str]) -> List[str]:
        # Pick up to BOOKS_PER_CATEGORY distinct books, or all if fewer exist
        unique_urls = list(dict.fromkeys(book_urls))
        sample_size = min(self.BOOKS_PER_CATEGORY, len(unique_urls))
        return self.rng.sample(unique_urls, sample_size)

    def handle_error(self, failure) -> None:
        # Log a failed request
        self.logger.error("Request failed: %s", repr(failure))