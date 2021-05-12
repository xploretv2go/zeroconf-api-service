add_cronjob () { 
    echo "Adding Zeroconf API as a cronjob"
    crontab -l > newcron
    echo "@reboot sh /home/pi/zeroconf.api.service/launcher.sh >/home/pi/logs/cronlog 2>&1" >> file
    crontab newcron
    rm -f newcron
}


if [[ -d "/home/pi/logs" ]];
 then
    echo "logs folder already exists"
    add_cronjob()
    
else 
    mkdir /home/pi/logs
    cd /home/pi/
    add_cronjob()
fi 
echo "please restart your raspberry pi to start the ZeroConfAPI"
