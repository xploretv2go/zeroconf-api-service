#!/bin/bash

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

#Defining variable for launcher
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )

launcher="${parent_path}/launcher-owrt.sh"


echo "Modifying hostname file"

if grep -q "localzeroconf" /etc/config/dhcp; then
	echo "Hostname already modified" 
else
	echo -e "\nconfig domain\n\toption name 'localzeroconf'\n\toption ip '192.168.192.2'" >> /etc/config/dhcp
	/etc/init.d/dnsmasq restart
	
	echo "DHCP successfully modified"
fi


if grep -q "lxc.uts.name = iot" /srv/lxc/iot/config; then
	echo "Hostname already modified"
else
	sed -i -e 's/lxc.uts.name = iot/lxc.uts.name = localzeroconf/g' /srv/lxc/iot/config
	lxc-stop --name iot
	lxc-start --name iot
	
	echo "DHCP successfully modified"
fi

echo "localzeroconf alias set!"

cp /etc/zeroconf.api.service/zeroconf /overlay/lxc/iot/rootfs/etc/init.d

lxc-attach --name iot

/etc/init.d/zeroconf enable


echo "Please restart your device to start the ZeroConfAPI"