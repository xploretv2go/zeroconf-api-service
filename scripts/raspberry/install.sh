#!/bin/bash

if [[ $EUID -ne 0 ]]
then
   echo "This script must be run as root" 
   exit 1
fi

#Defining variable for launcher
parent_path="$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )"

launcher="${parent_path}/launcher.sh"
service="${parent_path}/zeroconf-discovery.service"

#Testing if logs folder exists
#if [ -e "${parent_path}/logs" ]
#then
#	echo "Folder logs already exists"
#else
#	echo "Creating logs folder.."
#	mkdir ${parent_path}/logs
#    cd /
#fi

echo "Setting hostname"
raspi-config nonint do_hostname "zerodiscovery"

#echo "Modifying /etc/hosts file"


#if [[ $(sed -n '/^127.0.0.1/p' /etc/hosts) == *"zeroconf-discovery"* ]]; then
#	echo "IPv4 Host already modified"
#else
#	sed -i '/^127.0.0.1/ s/$/ zeroconf/' /etc/hosts
#	echo "IPv4 Host successfully modified"
#fi


#if [[ $(sed -n '/^::1/p' /etc/hosts) == *"ip6-zeroconf-discovery"* ]]; then
#	echo "IPv6 Host already modified"
#else
#	sed -i '/^::1/ s/$/ ip6-zeroconf/' /etc/hosts
#	echo "IPv6 Host successfully modified"
#fi

echo "Zerodiscovery hotname set!"

if [ -e $launcher ]
then
	echo "Launcher already exists"
else
	touch "${launcher}"
	printf '#!/bin/sh\n\nsudo pip3 install -r %s/../../requirements.txt\nsudo python3 %s/../../service_discovery/__init__.py' "${parent_path}" "${parent_path}" > "${launcher}"
	chmod 755 "${launcher}"
	echo "Launcher created"
fi

echo "Copying certificates"

mkdir -p /etc/zeroconf-api-service/certs

cp "${parent_path}/../../certs/fullchain.pem" "/etc/zeroconf-api-service/certs"
cp "${parent_path}/../../certs/privkey.pem" "/etc/zeroconf-api-service/certs"

echo "Certificates copied"

if [ -e $service ]
then
	echo "Service already exists"
else
	touch "${service}"
	printf '[Unit]\nDescription=Zeroconf service discovery\nAfter=multi-user.target\n[Service]\nRestart=always\nExecStart=%s\n[Install]\nWantedBy=multi-user.target' "${launcher}" > "${service}"
	chmod 755 "${launcher}"
	cp ${service} "/etc/systemd/system"
	systemctl enable zeroconf-discovery.service
	systemctl start zeroconf-discovery.service
	echo "Service created"
fi

echo "Done"

echo "Please reboot your device"
