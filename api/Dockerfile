FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

COPY api/requirements.txt requirements.txt
RUN pip install -r requirements.txt

RUN mkdir -p /app
COPY api/app /app

RUN mkdir -p /wait
COPY wait /wait

ENV PYTHONPATH=/
