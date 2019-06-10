FROM quickdeploy/yao-python3

MAINTAINER Newnius <newnius.cn@gmail.com>

RUN pip3 install docker kafka psutil

ADD bootstrap.sh /etc/bootstrap.sh

ADD monitor.py /root/monitor.py

ADD executor.py /root/executor.py

WORKDIR /root

CMD ["/etc/bootstrap.sh"]