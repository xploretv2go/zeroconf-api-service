#!/bin/bash
#uninstall.sh

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )
launcher="${parent_path}/launcher.sh"
logFile="${parent_path}/logs/cronlog"

remove_cronjob () { 
    echo "Removing Zeroconf API cronjob"
    crontab -l > newcron
    sed -e '/\@reboot.*launcher.sh.*$/d' newcron
    crontab newcron
	crontab -l | grep -i "@reboot sleep 10 && sh ${launcher} > $logFile 2>&1" | crontab -r
	if [ $? -eq 0 ]
		then
			echo "Cronjob removed!"
		else
			echo "Failed to remove cronjob!"
	fi
    rm -f newcron
}



echo "Are you sure you want to proceed with uninstallation? (Y/N)"
read ANSWER

case $ANSWER in

	Y|y)
		echo "Proceeding with uninstallation ..."
		sleep 1
		remove_cronjob
		sed -i 's/ zeroconf//' /etc/hosts
		sed -i 's/ ip6-zeroconf//' /etc/hosts

		echo "Removing all files and folders"
		rm -rf "${parent_path}/../.."
		echo "Uninstallation completed!";;
	N|n)
		echo "Uninstallation aborted!"
		exit 1;;
	*);;
esac
