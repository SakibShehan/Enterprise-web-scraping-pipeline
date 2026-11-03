# Enterprise Web Scraping Pipeline – Books Data Engineering System

A modular Scrapy application that discovers book categories dynamically from [Books to Scrape](https://books.toscrape.com/index.html), randomly selects 7 categories and up to 5 books from each, cleans the data through item pipelines, exports it to JSON, CSV and XML, stores it in SQLite, and can be deployed with Scrapyd and Docker.

## Contents

1. [Project Overview](#project-overview)
2. [Features](#features)
3. [Tech Stack](#tech-stack)
4. [Installation Guide](#installation-guide)
5. [Environment Setup](#environment-setup)
6. [Running the Spider](#running-the-spider)
7. [Docker Setup Guide](#docker-setup-guide)
8. [Scrapyd Deployment Guide](#scrapyd-deployment-guide)
9. [Output Format Description](#output-format-description)
10. [Database Configuration](#database-configuration)
11. [Architecture Diagram](#architecture-diagram)
12. [Folder Structure](#folder-structure)
13. [Design Decisions](#design-decisions)
14. [Known Limitations](#known-limitations)

---

## Project Overview

The project is an end-to-end scraping workflow built with Python and Scrapy. On every run it:

1. Starts at the website homepage and discovers all book categories (names and URLs) from the page itself. Nothing is hardcoded.
2. Randomly selects exactly **7 categories** out of all discovered categories.
3. Visits each selected category and follows pagination until the last page.
4. Randomly selects up to **5 distinct books** from each category. If a category has fewer than 5 books, all of its books are selected.
5. Opens each selected book's detail page and extracts six fields.
6. Passes every item through a cleaning pipeline, then a SQLite pipeline.
7. Writes the same cleaned items to `books.json`, `books.csv` and `books.xml` through Scrapy Feed Exports.

Target website: https://books.toscrape.com/index.html

## Features

- Dynamic category discovery: category names and URLs are not hardcoded.
- Pagination handled by following each page's `next` link, so sampling covers the whole category.
- Fixed-size category sampling: exactly 7 categories per run, chosen from all discovered categories regardless of their size.
- Random selection of up to 5 distinct books per category.
- Extraction of `title`, `price`, `availability`, `product_url`, `image_url` and `category`.
- Cleaning and normalization in a Scrapy Item Pipeline (whitespace, unicode, currency symbols, numeric price, Boolean availability).
- SQLite storage through a second Item Pipeline using parameterized SQL.
- Feed Exports for JSON, CSV and XML configured in `settings.py`.
- Optional `seed` spider argument to make category selection repeatable for debugging.
- Dockerfile and Docker Compose configuration for Scrapyd.
- Scrapyd deployment and spider execution through its HTTP API.
- Logging for discovery, selection, crawling, cleaning and errors.
- Object-oriented structure (parsers, sampler, spider, pipelines) with docstrings on classes and methods.

## Tech Stack

| Component | Details |
|---|---|
| Language | Python 3.12 (tested with 3.12.3) |
| Crawling framework | Scrapy 2.19.0 |
| Deployment server | Scrapyd |
| Deployment client | scrapyd-client |
| Database | SQLite (`sqlite3`, included with Python) |
| Containers | Docker and Docker Compose |

Exact installed versions are pinned in `requirements.txt`.

## Installation Guide

### Prerequisites

- Linux, macOS, or Windows with WSL
- Python 3.12 (recommended) and `pip`
- Git
- Docker Engine and Docker Compose (only for the Docker setup)

### Steps

```bash
https://github.com/SakibShehan/Enterprise-web-scraping-pipeline
cd Enterprise-web-scraping-pipeline

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On Windows PowerShell, activate the environment with `.venv\Scripts\Activate.ps1`.

Verify the installation:

```bash
python --version
scrapy version
scrapy list          # should print: books
scrapyd-deploy --help
```

## Environment Setup

The project needs no API keys or `.env` file. Configuration lives in `books_pipeline/settings.py`:

| Setting | Default | Purpose |
|---|---|---|
| `ROBOTSTXT_OBEY` | `True` | Respect `robots.txt` (a 404 means no restrictions) |
| `DOWNLOAD_DELAY` | `0.5` | Base delay between requests, in seconds |
| `DOWNLOAD_DELAY_JITTER` | `0.5` | Random variation of the delay (±50%) |
| `AUTOTHROTTLE_ENABLED` | `True` | Adapt request rate to server response time |
| `RETRY_TIMES` | `3` | Retries for failed requests |
| `DOWNLOAD_TIMEOUT` | `30` | Request timeout, in seconds |
| `LOG_LEVEL` | `INFO` | Use `DEBUG` for more detail |
| `ITEM_PIPELINES` | `BooksPipeline` (300), `SQLitePipeline` (400) | Cleaning runs before storage |
| `SQLITE_DB_PATH` | `books.db` | SQLite database file |
| `FEEDS` | JSON, CSV, XML | Output files, overwritten on every run |

Constants that control sampling are in `books_pipeline/spiders/books.py`:

| Constant | Value | Meaning |
|---|---|---|
| `CATEGORY_SAMPLE_SIZE` | `7` | Categories selected per run |
| `BOOKS_PER_CATEGORY` | `5` | Maximum books selected per category |

Settings can be overridden on the command line, for example `scrapy crawl books -s LOG_LEVEL=DEBUG` or `-s SQLITE_DB_PATH=/tmp/test.db`.

## Running the Spider

From the project root, with the virtual environment active:

```bash
scrapy list
scrapy crawl books
```

A normal run creates `books.json`, `books.csv`, `books.xml` and `books.db` in the current directory. Each new run overwrites the previous files and replaces the rows in the database.

Useful variations:

```bash
# Repeatable category selection (debugging)
scrapy crawl books -a seed=42

# More detailed logs
scrapy crawl books -L DEBUG

# Write one temporary file instead of using the FEEDS setting
scrapy crawl books -O test.json
```

Expected log lines:

```
[books] INFO: Starting crawl at https://books.toscrape.com/index.html
[books] INFO: Discovered 50 categories; randomly selected 7
[books] INFO: Category <name>: collected <N> books across <P> page(s)
[books] INFO: Category <name>: selected 5 of <N> books
[books] INFO: SQLite database ready: books.db
[books] INFO: SQLite database closed: books.db
```

The final stats should show `finish_reason: 'finished'` and an `item_scraped_count` of about 35 (see [Known Limitations](#known-limitations) for why it varies). A `robots.txt` 404 in the stats is expected.

### Checking that the outputs match

```bash
python - << 'PY'
import csv, json, sqlite3
import xml.etree.ElementTree as ET

with open("books.json", encoding="utf-8") as f:
    json_rows = json.load(f)
with open("books.csv", encoding="utf-8", newline="") as f:
    csv_rows = list(csv.DictReader(f))
xml_rows = [{c.tag: (c.text or "") for c in book}
            for book in ET.parse("books.xml").getroot()]

conn = sqlite3.connect("books.db")
db_rows = conn.execute(
    "SELECT title, price, availability, product_url, image_url, category FROM books"
).fetchall()
conn.close()

def flag(value):
    return 1 if str(value).lower() in ("true", "1") else 0

def key(r):
    return (r["title"], float(r["price"]), flag(r["availability"]),
            r["product_url"], r["image_url"], r["category"])

db_set = set(db_rows)
print("Counts  JSON/CSV/XML/DB:", len(json_rows), len(csv_rows), len(xml_rows), len(db_rows))
print("JSON == DB:", {key(r) for r in json_rows} == db_set)
print("CSV  == DB:", {key(r) for r in csv_rows} == db_set)
print("XML  == DB:", {key(r) for r in xml_rows} == db_set)
PY
```

All three comparisons should print `True`.

## Docker Setup Guide

The Docker image runs **Scrapyd** on port 6800. The project is then deployed into it with `scrapyd-deploy`, exactly as in a local setup.

Files involved: `Dockerfile`, `.dockerignore`, `compose.yaml`, `scrapyd.conf`.

- The image is based on `python:3.12-slim` and installs `requirements.txt`.
- Inside the container, Scrapyd listens on `0.0.0.0` and stores eggs, logs and job data in `/data` (a named volume, `scrapyd-data`).
- Compose publishes the API on `127.0.0.1:6800`, so it is not exposed to the network.
- The host file `books.db` is mounted at `/app/books.db`.

### Prerequisites

- Docker Engine and Docker Compose installed.
- Your user can run Docker (on Linux, it must be in the `docker` group, or use `sudo`).

### Build and start

```bash
touch books.db           # must exist, otherwise Docker creates a folder with this name
docker compose config    # validate the compose file
docker compose build
docker compose up -d
docker compose ps
```

Open http://127.0.0.1:6800/ to see the Scrapyd web interface.

### Useful commands

```bash
docker compose logs -f scrapyd     # follow logs
docker compose ps                  # status
docker compose down                # stop and remove the container (volume is kept)
docker compose down -v             # also delete the scrapyd-data volume
```

### Getting the feed files out of the container

Feed files from a Scrapyd job are written to `/app` inside the container. Copy them out with:

```bash
docker cp books-scrapyd:/app/books.json ./books.json
docker cp books-scrapyd:/app/books.csv ./books.csv
docker cp books-scrapyd:/app/books.xml ./books.xml
```

### Troubleshooting

| Problem | Fix |
|---|---|
| `permission denied ... /var/run/docker.sock` | Add your user to the `docker` group (`sudo usermod -aG docker $USER`), then log out and in. This needs admin rights. |
| `port is already allocated` | A local `scrapyd` is still running. Stop it with `Ctrl+C`. |
| `books.db` became a directory | `docker compose down`, `rm -rf books.db`, `touch books.db`, `docker compose up -d` |
| Permission error writing `books.db` | `chmod 666 books.db` |
| Spider fails with an import error | A dependency is missing from `requirements.txt`; check the job log. |

## Scrapyd Deployment Guide

### 1. Configuration files

`scrapy.cfg` defines the deploy target:

```ini
[settings]
default = books_pipeline.settings

[deploy:local]
url = http://127.0.0.1:6800/
project = books_pipeline
```

`setup.py` packages the project as an egg and exposes the Scrapy settings module. `scrapyd.conf` configures the server (port, directories, process limits). Scrapyd reads `scrapyd.conf` from the folder where it is started.

### 2. Start Scrapyd

Either use Docker (see above), or run it locally in its own terminal from the project root:

```bash
source .venv/bin/activate
scrapyd
```

### 3. Deploy the project

In another terminal, from the project root with the virtual environment active:

```bash
scrapyd-deploy local
```

A successful response contains `"status": "ok"`. Verify:

```bash
curl -s http://127.0.0.1:6800/listprojects.json
curl -s "http://127.0.0.1:6800/listspiders.json?project=books_pipeline"
```

### 4. Schedule a crawl through the API

```bash
curl -s -X POST http://127.0.0.1:6800/schedule.json \
  -d project=books_pipeline \
  -d spider=books
```

The response contains `"status": "ok"` and a `jobid`. Spider arguments can be passed as extra `-d` fields, for example `-d seed=42`.

### 5. Monitor the job

```bash
curl -s "http://127.0.0.1:6800/listjobs.json?project=books_pipeline"
```

The job moves from `pending` to `running` to `finished`. Logs are available in the web interface at http://127.0.0.1:6800/logs/ and on disk:

- Local Scrapyd: `logs/books_pipeline/books/<jobid>.log` in the folder where Scrapyd was started
- Docker: `/data/logs/books_pipeline/books/<jobid>.log` inside the container

```bash
# Docker example
docker compose exec scrapyd sh -c "grep -E 'Discovered|SQLite|item_scraped_count|ERROR' /data/logs/books_pipeline/books/*.log"
```

### 6. Other API calls

```bash
# Cancel a job
curl -s -X POST http://127.0.0.1:6800/cancel.json -d project=books_pipeline -d job=<jobid>

# Delete the deployed project version
curl -s -X POST http://127.0.0.1:6800/delproject.json -d project=books_pipeline
```

With a local Scrapyd, output files are written to the folder where `scrapyd` was started. With Docker they are written to `/app` in the container.

## Output Format Description

Each book record has six fields:

| Field | Type after processing | Description |
|---|---|---|
| `title` | String | Book title |
| `price` | Float | Price with the currency symbol removed (for example `51.77`) |
| `availability` | Boolean | `true` when the text starts with "In stock", otherwise `false` |
| `product_url` | String | Absolute URL of the book detail page |
| `image_url` | String | Absolute URL of the book cover image |
| `category` | String | Category name discovered from the homepage |

Feed exports are configured in `FEEDS` in `books_pipeline/settings.py` and overwrite the files on each run:

| File | Description |
|---|---|
| `books.json` | JSON array of records, indented, `price` as a number and `availability` as a Boolean |
| `books.csv` | Header row plus one row per book; column order is fixed in the `fields` list; availability appears as `True`/`False` |
| `books.xml` | `<books>` root with one `<book>` element per record |

Example JSON record:

```json
{
  "title": "A Light in the Attic",
  "price": 51.77,
  "availability": true,
  "product_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "image_url": "https://books.toscrape.com/media/cache/fe/72/fe72f0532301ec28892ae79a629a293c.jpg",
  "category": "Poetry"
}
```

Items reach the feeds only after all pipelines have run, so the feeds and the database hold the same cleaned data.

## Database Configuration

- Engine: SQLite, using Python's built-in `sqlite3` module.
- File: `books.db`, created in the working directory. Change it with the `SQLITE_DB_PATH` setting.
- Table `books`:

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER | Primary key, auto-increment |
| `title` | TEXT | Not null |
| `price` | REAL | Not null |
| `availability` | INTEGER | `1` for in stock, `0` otherwise (SQLite has no Boolean type) |
| `product_url` | TEXT | Not null |
| `image_url` | TEXT | |
| `category` | TEXT | Not null |

Inserts are handled by `SQLitePipeline` in `books_pipeline/pipelines.py` using parameterized queries. The connection opens in `open_spider`, which also creates the table and deletes the rows of the previous crawl, and closes in `close_spider`. `books.db` therefore always holds the latest crawl.

Inspect the database:

```bash
python - << 'PY'
import sqlite3
conn = sqlite3.connect("books.db")
print("Records:", conn.execute("SELECT COUNT(*) FROM books").fetchone()[0])
for row in conn.execute("SELECT category, COUNT(*) FROM books GROUP BY category ORDER BY category"):
    print(row)
conn.close()
PY
```

## Architecture Diagram

```
                  scrapy crawl books  /  Scrapyd schedule.json
                                   |
                                   v
                    settings.py (pipelines, feeds, limits)
                                   |
                                   v
        +-------------------- BooksSpider --------------------+
        |        (decides which request comes next)            |
        +------------------------------------------------------+
                                   |
   homepage response               |
        |-----> CategoryParser ----+--> 50 categories
        |-----> RandomSampler -------> 7 selected categories
        |
   category page (repeat until no next page)
        |-----> BookListParser -----> book URLs + next page URL
        |-----> RandomSampler -------> up to 5 books per category
        |
   book detail page
        |-----> BookDetailParser ---> BooksPipelineItem (raw)
                                   |
                                   v
                 BooksPipeline (priority 300): clean and validate
                                   |
                                   v
                 SQLitePipeline (priority 400): insert into books.db
                                   |
                                   v
                 Feed Exports: books.json | books.csv | books.xml

Deployment:  setup.py --> scrapyd-deploy --> Scrapyd API (schedule.json)
Container:   Dockerfile + compose.yaml --> Scrapyd service on port 6800
```

## Folder Structure

```
enterprise-web-scraping-pipeline/
├── books_pipeline/
│   ├── __init__.py
│   ├── items.py             # BooksPipelineItem (six fields)
│   ├── middlewares.py       # Generated Scrapy module (unused)
│   ├── parsers.py           # CategoryParser, BookListParser, BookDetailParser
│   ├── pipelines.py         # BooksPipeline (cleaning), SQLitePipeline (storage)
│   ├── sampler.py           # RandomSampler (random selection, seed)
│   ├── settings.py          # Feeds, pipelines, politeness, logging
│   └── spiders/
│       ├── __init__.py
│       └── books.py         # BooksSpider (crawl flow only)
├── .dockerignore
├── .gitignore
├── compose.yaml             # Docker Compose service for Scrapyd
├── Dockerfile               # Scrapyd image
├── README.md
├── requirements.txt
├── scrapy.cfg               # Settings module and deploy target
├── scrapyd.conf             # Scrapyd server configuration
├── setup.py                 # Egg packaging for scrapyd-deploy
├── books.json               # Generated by a crawl
├── books.csv                # Generated by a crawl
├── books.xml                # Generated by a crawl
└── books.db                 # Generated by a crawl
```

Generated outputs and the Scrapyd runtime folders (`eggs/`, `logs/`, `dbs/`) are listed in `.gitignore` and are not source files.

### Responsibilities

| File | Class | Responsibility |
|---|---|---|
| `spiders/books.py` | `BooksSpider` | Orchestrates requests and callbacks; builds every request through one helper that attaches the error handler |
| `parsers.py` | `CategoryParser` | Reads categories from the homepage sidebar |
| `parsers.py` | `BookListParser` | Reads book URLs and the next page link from a category page |
| `parsers.py` | `BookDetailParser` | Builds an item from a book detail page |
| `sampler.py` | `RandomSampler` | Picks distinct random items and owns the seed |
| `items.py` | `BooksPipelineItem` | Defines the record structure |
| `pipelines.py` | `BooksPipeline` | Trims and normalizes text, converts price and availability, drops invalid items |
| `pipelines.py` | `SQLitePipeline` | Creates the table, inserts items, closes the connection |

## Design Decisions

- **Dynamic discovery:** categories are read from the homepage sidebar with a selector that skips the parent "Books" link, so no names or URLs are stored in code.
- **Fixed category sample:** exactly 7 categories are chosen at random from all discovered ones, without checking their size first.
- **Pagination before sampling:** the spider carries the collected book URLs from page to page and samples only on the last page, so books from every page have an equal chance of being picked.
- **"Up to 5" books:** the assignment asks for exactly 5 books per category, but some categories contain fewer than 5. In that case all available books are selected instead of failing the crawl or inventing data.
- **Single random selection:** sampling happens once, in the spider. The feeds and the database receive the same items, which keeps them consistent.
- **Clean first, then store:** `BooksPipeline` (300) runs before `SQLitePipeline` (400), and feeds receive items after both.
- **Separation of responsibilities (SOLID):** parsing, sampling, crawl control, cleaning and storage are separate classes. The spider receives its parsers and sampler through `__init__`, so they can be replaced in tests.
- **DRY:** one sampler serves both selections, one request helper serves every request, and one loop cleans all text fields.
- **Parameterized SQL:** inserts use placeholders, never string-built queries.
- **Dropping bad items:** an item with a missing title or an unparseable price raises `DropItem` and is logged, so it is excluded from every storage format.
- **Seed argument:** `-a seed=<value>` makes selection repeatable. It is a debugging aid; without it, selection is random.
- **SQLite:** needs no extra container or service, which keeps the Docker setup to a single Scrapyd service.
- **Docker publishes on localhost only:** Scrapyd has no authentication, so the API is bound to `127.0.0.1`.
- **Logging:** each stage logs what it did (discovery, selection, pages, cleaning, storage), and failed requests go to a common error handler.

## Known Limitations

- **Record count varies.** Exactly 7 categories are chosen, but each contributes up to 5 books, and some categories have fewer than 5. The total is about 35 but not always a multiple of 5.
- **Seeded runs are only partly repeatable.** The same seed always selects the same 7 categories. Book selection shares one random generator across categories that finish in a varying order, so the chosen books can differ between seeded runs.
- **Latest-run storage only.** SQLite is cleared at the start of every crawl and feed files are overwritten. It is not a historical archive. Do not run concurrent jobs against the same database file.
- **Feed files in Docker stay inside the container** unless copied out with `docker cp`. Only `books.db` is mounted to the host. A host-mounted output directory would be a useful improvement.
- **No Scrapyd authentication.** The API is protected only by binding to localhost. Do not expose port 6800 publicly without a reverse proxy and authentication.
- **Dependence on the site's HTML.** The CSS selectors in `parsers.py` must be updated if the website layout changes.
- **`robots.txt` returns 404** on the target site. Scrapy treats this as no restrictions and the crawl completes, but the behavior should be monitored.
- **Availability** is `true` only when the text begins with "In stock"; any other text, including unexpected wording, becomes `false`.
- **Educational scope.** For production use, add automated tests, stronger retry and alerting policies, schema-level validation, deduplication across runs, and configuration through environment variables.
- **Docker setup status.** The Docker files are provided and the compose file validates with `docker compose config`, but the image build and a full run inside Docker should be confirmed on a machine where Docker access is available before relying on this section.