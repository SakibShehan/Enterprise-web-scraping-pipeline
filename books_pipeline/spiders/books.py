from typing import Dict, List

import scrapy
from scrapy.http import Response


class BooksSpider(scrapy.Spider):
    #Crawl Books to Scrape starting from its homepage

    name = "books"
    allowed_domains = ["books.toscrape.com"]
    start_url = "https://books.toscrape.com/index.html"

    CATEGORY_LINK_SELECTOR = "div.side_categories ul.nav-list > li > ul > li > a"

    async def start(self):
   
        self.logger.info("Starting crawl at %s", self.start_url)
        yield scrapy.Request(
            self.start_url,
            callback=self.parse,
            errback=self.handle_error,
        )

    def parse(self, response: Response) -> None:
        #Handle the homepage response and discover all categories.

        categories = self.extract_categories(response)

        if not categories:
            self.logger.error(
                "No categories found on %s; the page layout may have changed.",
                response.url,
            )
            return

        self.logger.info("Discovered %d categories", len(categories))
        for category in categories:
            self.logger.debug(
                "Category found: %s -> %s", category["name"], category["url"]
            )

        self.categories = categories

    def extract_categories(self, response: Response) -> List[Dict[str, str]]:
        #Extract category names and absolute URLs from the sidebar.

        categories = []
        for link in response.css(self.CATEGORY_LINK_SELECTOR):
            name = " ".join(link.css("::text").get(default="").split())
            href = link.attrib.get("href")
            if not name or not href:
                self.logger.warning("Skipping malformed category link: %s", link.get())
                continue
            categories.append({"name": name, "url": response.urljoin(href)})
        return categories

    def handle_error(self, failure) -> None:
   
        self.logger.error("Request failed: %s", repr(failure))