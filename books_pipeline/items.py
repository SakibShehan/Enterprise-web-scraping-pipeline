import scrapy


class BooksPipelineItem(scrapy.Item):
    #Container for one scraped book record.

    title = scrapy.Field()
    price = scrapy.Field()
    availability = scrapy.Field()
    product_url = scrapy.Field()
    image_url = scrapy.Field()
    category = scrapy.Field()