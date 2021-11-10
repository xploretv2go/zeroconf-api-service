#!/bin/sh
#launcher.sh



cd "$(dirname "$0")"
sudo pip3 install -r requirements.txt
sudo python3 service_discovery/__init__.py runserver
cd /
