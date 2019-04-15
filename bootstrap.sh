#!/usr/bin/env bash

# TODO: monitor the processes

python3 /root/monitor.py &

python3 /root/executor.py &

sleep infinity