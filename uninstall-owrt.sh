#!/bin/sh
#uninstall.sh

parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )


echo "Are you sure you want to proceed with uninstallation? (Y/N)"
read ANSWER

case $ANSWER in

	Y|y)
		echo "Proceeding with uninstallation ..."
		sleep 1
		sed -i "1N;1N;/\nconfig domain$/{N;N;d};P;N;D" /etc/config/dhcp
		/etc/init.d/dnsmasq restart

		sed -i -e 's/lxc.uts.name = localzeroconf/lxc.uts.name = iot/g' /srv/lxc/iot/config

        echo "Removing zeroconf file from /overlay/lxc/iot/rootfs/etc/init.d/"
        rm -rf /overlay/lxc/iot/rootfs/etc/init.d/zeroconf

		echo "Removing all files and folders"
		rm -R $parent_path  2>&1 > /dev/null

		lxc-stop --name iot
		lxc-start --name iot

		echo "Uninstallation completed!";;
	N|n)
		echo "Uninstallation aborted!"
		exit 1;;
	*);;
esac