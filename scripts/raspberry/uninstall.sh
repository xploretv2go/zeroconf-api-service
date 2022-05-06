#!/bin/bash
#uninstall.sh

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
launcher="${parent_path}/launcher.sh"
logFile="${parent_path}/logs/cronlog"



echo "Are you sure you want to proceed with uninstallation? (Y/N)"
read ANSWER

case $ANSWER in

	Y|y)
		echo "Proceeding with uninstallation ..."
		sleep 1

		systemctl stop zeroconf-discovery.service
		systemctl disable zeroconf-discovery.service

		rm /etc/systemd/system/zeroconf-discovery.service

		rm -r /etc/zeroconf-api-service/

		raspi-config nonint do_hostname "raspberry"

		echo "Removing all files and folders"
		cd ../..
		rm -rf "$(pwd)"

		echo "Please reboot your device"
		echo "Uninstallation completed!";;
	N|n)
		echo "Uninstallation aborted!"
		exit 1;;
	*);;
esac
