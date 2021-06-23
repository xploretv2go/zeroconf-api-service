#!/bin/sh

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



#Adding Zeroconf API to crontab
add_cronjob () { 
    echo "Adding Zeroconf API as a cronjob"
    crontab -l > newcron
    echo "@reboot sh ${launcher} > $logFile 2>&1" >> newcron
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