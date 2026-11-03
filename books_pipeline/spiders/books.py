from typing import Dict, List, Optional

import scrapy
from scrapy.http import Response

from books_pipeline.parsers import BookDetailParser, BookListParser, CategoryParser
from books_pipeline.sampler import RandomSampler


class BooksSpider(scrapy.Spider):
    """Crawl Books to Scrape and yield a random sample of books."""

    name = "books"
    allowed_domains = ["books.toscrape.com"]
    start_url = "https://books.toscrape.com/index.html"

    CATEGORY_SAMPLE_SIZE = 7
    BOOKS_PER_CATEGORY = 5

    def __init__(
        self,
        seed: Optional[str] = None,
        sampler: Optional[RandomSampler] = None,
        category_parser: Optional[CategoryParser] = None,
        book_list_parser: Optional[BookListParser] = None,
        book_parser: Optional[BookDetailParser] = None,
        *args,
        **kwargs,
    ):
        """Set up the spider; collaborators can be injected for testing."""
        super().__init__(*args, **kwargs)
        self.seed = seed
        self.sampler = sampler or RandomSampler(seed)
        self.category_parser = category_parser or CategoryParser()
        self.book_list_parser = book_list_parser or BookListParser()
        self.book_parser = book_parser or BookDetailParser()

    def make_request(self, url: str, callback, **cb_kwargs) -> scrapy.Request:
        """Build a request that always logs failures."""
        return scrapy.Request(
            url,
            callback=callback,
            errback=self.handle_error,
            cb_kwargs=cb_kwargs,
        )

    async def start(self):
        """Send the first request to the homepage."""
        self.logger.info("Starting crawl at %s", self.start_url)
        yield self.make_request(self.start_url, self.parse)

    def parse(self, response: Response):
        """Discover categories, select a random sample, crawl each one."""
        categories = self.category_parser.parse(response)

        if not categories:
            self.logger.error(
                "No categories found on %s; the page layout may have changed.",
                response.url,
            )
            return

        selected = self.select_categories(categories)
        self.logger.info(
            "Discovered %d categories; randomly selected %d",
            len(categories),
            len(selected),
        )

        for category in selected:
            self.logger.info(
                "Selected category: %s -> %s", category["name"], category["url"]
            )
            yield self.make_request(
                category["url"],
                self.parse_category,
                category=category["name"],
                book_urls=[],
                pages=0,
            )

    def parse_category(
        self, response: Response, category: str, book_urls: List[str], pages: int
    ):
        """Collect book URLs across pages, then sample books on the last page."""
        pages += 1
        page_urls, next_url = self.book_list_parser.parse(response)
        book_urls = book_urls + page_urls
        self.logger.debug(
            "Category %s page %d: %d books", category, pages, len(page_urls)
        )

        if next_url:
            yield self.make_request(
                next_url,
                self.parse_category,
                category=category,
                book_urls=book_urls,
                pages=pages,
            )
            return

        self.logger.info(
            "Category %s: collected %d books across %d page(s)",
            category,
            len(book_urls),
            pages,
        )

        selected_urls = self.sampler.sample(book_urls, self.BOOKS_PER_CATEGORY)
        self.logger.info(
            "Category %s: selected %d of %d books",
            category,
            len(selected_urls),
            len(book_urls),
        )
        for url in selected_urls:
            yield self.make_request(url, self.parse_book, category=category)

    def parse_book(self, response: Response, category: str):
        """Yield the item extracted from a book detail page."""
        item = self.book_parser.parse(response, category)
        if item is not None:
            self.logger.debug("Extracted book [%s]: %s", category, item["title"])
            yield item

    def select_categories(
        self, categories: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Randomly pick distinct categories, or all if fewer exist."""
        if len(categories) < self.CATEGORY_SAMPLE_SIZE:
            self.logger.warning(
                "Only %d categories available; selecting all of them.",
                len(categories),
            )
        return self.sampler.sample(
            categories, self.CATEGORY_SAMPLE_SIZE, key=lambda c: c["url"]
        )

    def handle_error(self, failure) -> None:
        """Log a failed request."""
        self.logger.error("Request failed: %s", repr(failure))