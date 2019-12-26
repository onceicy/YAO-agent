#!/usr/bin/env bash

# run nvidia-smi in background to speed up the query and reduce CPU load (why?)
nvidia-smi daemon

python3 /root/agent.py