#!/bin/sh
#launcher.sh
# launcher script for openWRT

exec 3>&1 4>&2
trap 'exec 2>&4 1>&3' 0 1 2 3
exec 1>/etc/zeroconf.api.service/logs/log.out 2>&1


cd "$(dirname "$0")"
pip3 install -r requirements.txt
python3 ./run.py &
cd /