FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scrapyd.conf .

# Container-only changes: listen on all interfaces, store data in /data
RUN mkdir -p /data \
    && sed -i \
        -e 's/^bind_address.*/bind_address = 0.0.0.0/' \
        -e 's#^eggs_dir.*#eggs_dir     = /data/eggs#' \
        -e 's#^logs_dir.*#logs_dir     = /data/logs#' \
        -e 's#^dbs_dir.*#dbs_dir      = /data/dbs#' \
        scrapyd.conf

EXPOSE 6800

CMD ["scrapyd"]
