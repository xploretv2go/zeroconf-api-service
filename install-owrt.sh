#!/bin/bash

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

#Defining variable for launcher
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )

launcher="${parent_path}/launcher-owrt.sh"


echo "Modifying /etc/hosts file"


if [[ $(sed -n '/^127.0.0.1/p' /etc/hosts) == *"localzeroconf"* ]]; then
	echo "IPv4 Host already modified"
else
	sed -i '/^127.0.0.1/ s/$/ localzeroconf/' /etc/hosts
	echo "IPv4 Host successfully modified"
fi


if [[ $(sed -n '/^::1/p' /etc/hosts) == *"ip6-localzeroconf"* ]]; then
	echo "IPv6 Host already modified"
else
	sed -i '/^::1/ s/$/ localzeroconf/' /etc/hosts
	echo "IPv6 Host successfully modified"
fi

echo "Localzeroconf alias set!"

cp /etc/zeroconf.api.service/zeroconf /overlay/lxc/iot/rootfs/etc/init.d 

lxc-attach --name iot

/etc/init.d/zeroconf enable


echo "Please restart your device to start the ZeroConfAPI"
