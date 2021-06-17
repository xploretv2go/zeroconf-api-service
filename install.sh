#!/bin/sh

#Defining variable for launcher
launcher=/home/pi/zeroconf.api.service/launcher.sh
logFile=/home/pi/zeroconf.api.service/logs/cronlog


#Adding Zeroconf API to crontab
add_cronjob () { 
    echo "Adding Zeroconf API as a cronjob"
    crontab -l > newcron
    echo "@reboot sh /home/pi/zeroconf.api.service/launcher.sh > $logFile 2>&1" >> newcron
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
	echo "Please restart your raspberry pi to start the ZeroConfAPI"
fi