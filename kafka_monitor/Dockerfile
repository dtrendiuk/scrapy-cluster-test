FROM python:3.8-slim-buster

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

ARG ENVIRONMENT=local

RUN apt-get update \
  # dependencies for building Python packages
  && apt-get install -y build-essential git bash\
  # psycopg2 dependencies
  && apt-get install -y libpq-dev \
  # Translations dependencies
  && apt-get install -y gettext \
  # cleaning up unused files
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# Allows docker to cache installed dependencies between builds
COPY kafka_monitor/requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Adds our application code to the image
COPY kafka_monitor /code
WORKDIR /code

RUN mkdir -p /wait
COPY wait /wait

RUN mkdir -p /scrapy_project
COPY scrapy_project /scrapy_project
COPY config/${ENVIRONMENT}/scrapy.cfg /scrapy_project/scrapy.cfg

RUN ["chmod", "+x", "/code/entrypoint.sh"]

CMD ["/code/entrypoint.sh"]
