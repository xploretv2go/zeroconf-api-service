#!/bin/sh
#launcher.sh
# launcher script for openWRT


cd "$(dirname "$0")"
pip3 install -r requirements.txt
python3 run.py
cd /
