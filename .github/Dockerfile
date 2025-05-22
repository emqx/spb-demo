FROM ubuntu:22.04

USER root

ENV TZ=Asia/Shanghai \
    DEBIAN_FRONTEND=noninteractive

RUN apt update \
    && apt install -y tzdata \
    && ln -fs /usr/share/zoneinfo/${TZ} /etc/localtime \
    && echo ${TZ} > /etc/timezone \
    && dpkg-reconfigure --frontend noninteractive tzdata \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get -y update && apt-get -y install \
	sudo pkg-config git gcc openssl libssl-dev alien unzip python3 python3-pip wget curl
RUN apt-get -y install gcc g++ cmake

RUN pip3 install uv

COPY ./spb-demo /root/spb-demo

RUN cd /root/spb-demo && uv sync
RUN cd /root/spb-demo && cp .env.example .env

COPY ./entrypoint.sh /usr/bin/entrypoint.sh
ENTRYPOINT ["/usr/bin/entrypoint.sh"]
EXPOSE 8080

