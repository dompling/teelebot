FROM python:alpine

LABEL maintainer="github.com/plutobell"
LABEL description="teelebot is a robot framework based on Telegram Bot API, with plug-in system, easy to extend."
LABEL source="https://github.com/plutobell/teelebot"

RUN apk add --no-cache --virtual .build-deps tzdata \
    && cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone \
    && apk del .build-deps \
    && pip3 install --no-cache-dir teelebot \
    && mkdir /config && mkdir /plugins

RUN apk add gcc musl-dev linux-headers lz4-dev\
    && pip3 install lz4 python-115 

RUN history -c


ENTRYPOINT ["teelebot", "-c", "/config/config.cfg", "-p", "/plugins"]