#!/bin/bash

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

#Defining variable for launcher
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )

launcher="${parent_path}/launcher.sh"
logFile="${parent_path}/logs/cronlog"

#Testing if logs folder exists
if [ -e "${parent_path}/logs" ]
then
	echo "Folder logs already exists"
else
	echo "Creating logs folder.."
	mkdir ${parent_path}/logs
    cd /
fi

echo "Modifying /etc/hosts file"


if [[ $(sed -n '/^127.0.0.1/p' /etc/hosts) == *"zeroconf"* ]]; then
	echo "IPv4 Host already modified"
else
	sed -i '/^127.0.0.1/ s/$/ zeroconf/' /etc/hosts
	echo "IPv4 Host successfully modified"
fi


if [[ $(sed -n '/^::1/p' /etc/hosts) == *"ip6-zeroconf"* ]]; then
	echo "IPv6 Host already modified"
else
	sed -i '/^::1/ s/$/ ip6-zeroconf/' /etc/hosts
	echo "IPv6 Host successfully modified"
fi

echo "Localzeroconf alias set!"

if [ -e $launcher ]
then
	echo "Launcher already exists"
else
	touch "${launcher}"
	printf '#!/bin/sh\n\nsudo pip3 install -r %s/requirements.txt\nsudo python3 %s/service_discovery/__init__.py' "${parent_path}" "${parent_path}" > "${launcher}"
	chmod 755 "${launcher}"
	echo "Launcher created"
fi

#Adding Zeroconf API to crontab
add_cronjob () { 
    echo "Adding Zeroconf API as a cronjob"
    crontab -l > newcron
    echo "@reboot sleep 10 && sh ${launcher} > $logFile 2>&1" >> newcron
    crontab newcron
    rm -f newcron
}

  
crontab -l | grep "$launcher"
if [ $? -eq 0 ]
	then
	    echo "Job already added to crontab"
    else
	    echo "Adding job to crontab..."
	    add_cronjob
fi

if [ -e $logFile ]
then
	echo "File '$logFile' is already created"
else
	echo "Starting service"
	sh ${launcher} > $logFile 2>&1 &
	echo "Done."
fi