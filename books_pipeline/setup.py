from setuptools import find_packages, setup

setup(
    name="books_pipeline",
    version="1.0",
    packages=find_packages(),
    entry_points={"scrapy": ["settings = books_pipeline.settings"]},
)