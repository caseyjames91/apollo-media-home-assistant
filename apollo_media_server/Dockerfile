ARG BUILD_FROM
ARG BUILD_VERSION
FROM ${BUILD_FROM}

ENV APOLLO_VERSION=${BUILD_VERSION}

RUN apk add --no-cache py3-pip
WORKDIR /opt/apollo

COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY app ./app
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
