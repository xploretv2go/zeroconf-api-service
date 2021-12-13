#!/bin/bash

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

#Defining variable for launcher
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )

launcher="${parent_path}/launcher-owrt.sh"
container=$(echo $(lxc-ls) | cut -d \t -f 1)


echo "Modifying hostname file"

#if grep -q "zeroconf" /etc/config/dhcp; then
#	echo "Hostname already modified" 
#else
#	echo -e "\nconfig domain\n\toption name 'zeroconf'\n\toption ip '192.168.3.111'" >> /etc/config/dhcp
#	/etc/init.d/dnsmasq restart
#	
#	echo "DHCP successfully modified"
#fi


if grep -q "lxc.uts.name = zeroconf" "/srv/lxc/${container}/config"; then
	echo "Hostname already modified"
else
	sed -i -e "s/lxc.uts.name = ${container}/lxc.uts.name = zeroconf/g" "/srv/lxc/${container}/config"
	lxc-stop --name "${container}"
	lxc-start --name "${container}"
	
	echo "DHCP successfully modified"
fi

echo "zeroconf alias set!"

cp "/etc/zeroconf.api.service/zeroconf" "/overlay/lxc/${container}/rootfs/etc/init.d"

lxc-attach --name "${container}"

/etc/init.d/zeroconf enable


echo "Please restart your device to start the ZeroConfAPI"