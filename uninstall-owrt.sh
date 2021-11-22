#!/bin/sh
#uninstall.sh

parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )


echo "Are you sure you want to proceed with uninstallation? (Y/N)"
read ANSWER

case $ANSWER in

	Y|y)
		echo "Proceeding with uninstallation ..."
		sleep 1
		sed -i 's/ localzeroconf//' /etc/hosts
		sed -i 's/ ip6-localzeroconf//' /etc/hosts

        echo "Removing zeroconf file from /overlay/lxc/iot/rootfs/etc/init.d/"
        rm -rf /overlay/lxc/iot/rootfs/etc/init.d/zeroconf

		echo "Removing all files and folders"
		rm -R $parent_path  2>&1 > /dev/null
		echo "Uninstallation completed!";;
	N|n)
		echo "Uninstallation aborted!"
		exit 1;;
	*);;
esac