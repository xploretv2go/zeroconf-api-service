#!/bin/sh
#launcher.sh


cd /
cd home/pi/zeroconf.api.service
sudo pip3 install -r requirements.txt
sudo python3 run.py
cd /