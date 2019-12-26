#!/usr/bin/env bash

# TODO: monitor the processes

# run nvidia-smi in background to speed up the query and reduce CPU load (why?)
nvidia-smi daemon

#python3 /root/monitor.py &

#python3 /root/executor.py &

#sleep infinity

python3 /root/main.py