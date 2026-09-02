ARG BUILD_FROM
ARG BUILD_VERSION
FROM ${BUILD_FROM}
ARG BUILD_VERSION

ENV APOLLO_VERSION=${BUILD_VERSION}

RUN apk add --no-cache py3-pip ca-certificates nodejs npm
WORKDIR /opt/apollo

COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY youtube_bridge ./youtube_bridge
RUN cd /opt/apollo/youtube_bridge && npm install --omit=dev

COPY app ./app
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
