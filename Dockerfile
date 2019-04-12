FROM quickdeploy/yao-python3

MAINTAINER Newnius <newnius.cn@gmail.com>

RUN pip3 install docker kafka

ADD bootstrap.sh /etc/bootstrap.sh

ADD yao-agent.py /root/yao-agent.py
ADD server.py /root/server.py

WORKDIR /root

CMD ["/etc/bootstrap.sh"]