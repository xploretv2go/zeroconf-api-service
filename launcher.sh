#!/bin/sh
#launcher.sh



cd "$(dirname "$0")"
sudo pip3 install -r requirements.txt
sudo python3 run.py
cd /
