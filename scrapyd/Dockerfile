# Scrapyd web service (with authentication)

FROM python:3.8

# install Ubuntu packages
ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update -qq \
 && apt-get install --no-install-recommends -y \
    git \
    # scrapy dependencies
    build-essential python3-dev \
    libxml2-dev libxslt1-dev zlib1g-dev libffi-dev libssl-dev \
    # nginx and htpasswd
    nginx apache2-utils \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

RUN python3 -m pip install --upgrade pip

# install Chaperone
# (Unofficial repo due to: https://github.com/garywiz/chaperone/issues/24)
#RUN pip3 install chaperone \
RUN pip3 install git+https://github.com/necrophcodr/chaperone.git \
 && mkdir /etc/chaperone.d

# install Scrapyd and dependencies
ADD scrapyd/requirements.txt /
RUN pip3 install -r /requirements.txt \
 && pip3 freeze > /pip3-freeze.txt

# Install Sellgo Core
ADD /core /core
RUN pip install -e /core

# Install scrapy_project dependencies
ADD scrapy_project/requirements.txt /scrapy_project_reqs.txt
RUN pip3 install -r /scrapy_project_reqs.txt

# configure
ADD scrapyd/chaperone.conf /etc/chaperone.d/chaperone.conf
ADD scrapyd/nginx.conf /etc/nginx/sites-enabled/default
ADD scrapyd/scrapyd.conf /etc/scrapyd/scrapyd.conf

# expose
VOLUME /scrapyd
EXPOSE 6800

ENTRYPOINT ["/usr/local/bin/chaperone"]
