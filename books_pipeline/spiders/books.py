import random
from typing import Dict, List, Optional

import scrapy
from scrapy.http import Response


class BooksSpider(scrapy.Spider):
    # Crawl Books to Scrape starting from its homepage

    name = "books"
    allowed_domains = ["books.toscrape.com"]
    start_url = "https://books.toscrape.com/index.html"

    CATEGORY_SAMPLE_SIZE = 7
    CATEGORY_LINK_SELECTOR = "div.side_categories ul.nav-list > li > ul > li > a"

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

    def parse(self, response: Response) -> None:
        # Discover all categories and select a random sample
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

    def handle_error(self, failure) -> None:
        # Log a failed request
        self.logger.error("Request failed: %s", repr(failure))