FROM nvidia/cuda:9.0-base

MAINTAINER Newnius <newnius.cn@gmail.com>

RUN apt update && \
	apt install -y python3 python3-pip

RUN pip3 install docker kafka

ADD bootstrap.sh /etc/bootstrap.sh

ADD yao-agent.py /root/yao-agent.py
ADD server.py /root/server.py

WORKDIR /root

CMD ["/etc/bootstrap.sh"]