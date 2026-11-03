import scrapy


class BooksPipelineItem(scrapy.Item):
    """One scraped book record shared by the spider, pipelines and feeds."""

    title = scrapy.Field()
    price = scrapy.Field()
    availability = scrapy.Field()
    product_url = scrapy.Field()
    image_url = scrapy.Field()
    category = scrapy.Field()