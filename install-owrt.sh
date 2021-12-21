#!/bin/bash

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

#Defining variable for launcher
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )

launcher="${parent_path}/launcher-owrt.sh"
container=$(echo $(lxc-ls) | cut -d \t -f 1)

echo "Installing python"
opkg update
opkg install python3
opkg install python3-pip

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
fi

echo "zeroconf alias set!"

touch "${parent_path}/zeroconf"

echo "Stopping container"
lxc-stop -n "${container}"

printf '#!/bin/sh /etc/rc.common\n\nUSE_PROCD=1\nSTART=95\nSTOP=01\nstart_service() {\n\tprocd_open_instance\n\tprocd_set_param command /bin/sh %s/launcher-owrt.sh\n\tprocd_set_param stdout 1\n\tprocd_set_param stderr 1\n\tprocd_close_instance\n}\n\nstop_service() {\n\tkillall python3\n}' "${parent_path}" > "${parent_path}/zeroconf"

mv "${parent_path}/zeroconf" "/overlay/lxc/${container}/rootfs/etc/init.d"
chmod 755 "/overlay/lxc/${container}/rootfs/etc/init.d/zeroconf"

touch "${parent_path}/launcher-owrt.sh"

printf '#!/bin/sh\npip3 install -r %s/requirements-owrt.txt\npython3 %s/service_discovery/__init__.py' "${parent_path}" "${parent_path}" > "${parent_path}/launcher-owrt.sh"
chmod 755 "${parent_path}/launcher-owrt.sh"

echo "Starting container"
lxc-start -n "${container}"
lxc-attach -n "${container}" -- /etc/init.d/zeroconf enable

echo "Finished"