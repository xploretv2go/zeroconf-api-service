#!/bin/sh
#launcher.sh
# launcher script for openWRT


cd "$(dirname "$0")"
pip3 install -r requirements.txt
sudo python3 service_discovery/__init__.py runserver
cd /
