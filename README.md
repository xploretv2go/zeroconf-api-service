# zeroconf.api.service
You need to list and resolve or announce existing Zeroconf services, but you cannot implement your own mDNS/DNS-SD feature? Then this REST API is the right solution, because you can browse and register Zeroconf services via it.

# Zeroconf Service Discovery API

This service browses the published zeroconf services in the local network of the server where the service is running and returns the results of the browse through the specified API GET endpoint. A service can be also registered by the API user through the POST method in /services endpoint.

The part of the service is a module which scans the network for availible types of services present on the network at any given time when the service is started. This module plays an important role in this project as it the found types are stored into a compact database storage(https://docs.python.org/3/library/shelve.html). These types are upon every start of the API seeded into the handler which collects the availible services on the network. This behaviour results in API being able to discover more services when it's restarted.  

Compatible with: 
  * Avahi
  * Bonjour

## Documentation

Swagger documentation in YAML format is availible in in the /docs directory full path is `/docs/zeroconf_api.yaml`

## Installing and running on a development server / localhost
1. Clone the repository & navigate to directory and run:
- `sudo git clone https://github.com/xploretv2go/zeroconf.api.service.git`
- In case pip3 is not installed with python3 on the system run `sudo apt-get install python3-pip`
- `sudo pip3 install -r requirements.txt`
- `sudo python3 run.py`
1. You're done!

## Deploying on a Rpi
To deploy the Zeroconf service/API on a device such as Rpi. Make sure you have [Avahi](https://www.avahi.org/) installed on the device

1. Make sure you have git version control installed. if not run:
   - `sudo apt-get install git` 
2. Navigate to you home directory where you wish to install the API service and type the command:
   - `sudo git clone https://github.com/xploretv2go/zeroconf.api.service.git`
3. Run installation script as a root to install the API on to your device:
   - `sudo bash install.sh` or `sudo sh install.sh`
4. Restart the Rpi using the command 
   - `sudo reboot`
5. After the restart check the newly created log file found in 
   - `zeroconf.api.service/logs/cronlog` 
   - to see if the log is populated with logging output from API
6. You can configure the port to be used by the API in file:
   - `/zeroconf.api.service/.env` 

To test the API through the command line use the following command to call the GET endpoint:

- `curl -X 'GET' 'http://localhost:15051/a1/xploretv/v1/zeroconf'` 

The output shown in the terminal after the command execution will have the following structure:

```
{
    "services": [
        {
            "name": "ZeroConf Service Discovery API at Frantiseks-MacBook-Pro",
            "hostName": "Frantiseks-MacBook-Pro.local.",
            "domainName": "local",
            "addresses": {
                "ipv4": [
                    "192.168.0.19"
                ],
                "ipv6": [
                    "fe80::1cb5:b8:f032:58d3%en0"
                ]
            },
            "service": {
                "type": "_http._tcp.local.",
                "port": 15051,
                "txtRecord": {
                    "get": "/a1/xploretv/v1/zeroconf"
                }
            }
        }
    ]
}
```


Note: you can configure the `port`, `hostname` and set`DEBUG` level in the `.env` file

## Installing and running on OpenWRT system
1. make sure to update the packages first by running `opkg update`
2. Install git-http package `opkg install git-http` and `opkg install ca-bundle`
3. Clone this repo `git clone https://github.com/xploretv2go/zeroconf.api.service.git` in `/etc` folder
4. Install python3 interpreter along with pip by running `opkg install python3` and `opkg install python3-pip`
5. After installing python3 and pip run following command to update pip `pip3 install --upgrade pip`
6. Run `sh install-owrt.sh` to install all the dependencies and set the crontab to start the API
7. Reboot the system using `reboot` command.
8. After the reboot run `/etc/init.d/cron start` to start cron

Note: In case there's an issue during the installation of packages specified in `requirement.txt` such as package `netifaces` run command 
`pip3 install wheel` or consider uninstalling python3 interpreter and installing python-dev package by running `opkg update` and `opkg install python-dev`


## Installing and running in a docker container
1. Install Docker.
- `curl -sSL https://get.docker.com | sh`
2. Add permission to user.
- `sudo usermod -aG docker <user>`
3. Install additional dependencies.
- `sudo apt-get install -y libffi-dev libssl-dev`
- `sudo apt-get install -y python3 python3-pip`
- `sudo apt-get remove python-configparser`
4. Install docker compose.
- `sudo pip3 -v install docker-compose`
5. After finishing docker installation make sure to logout and login to your system user account.
6. Navigate to a folder of your choice and clone this repository
- `git clone git@github.com:Frantisekf/zeroconf-service-discovery-API.git`
8. After cloning the repository step into it and build the application:
- `cd zeroconf-service-discovery`
- `docker-compose build`
9. To run the application, run this command from the zeroconf-service-discovery-API directory:
- `docker-compose up`
10. You're done!



Note: you can configure the `port`, `hostname` and set`DEBUG` level in the `.env` file

## API Usage
### List all services

**Definition**

`GET /zeroconf`

**Response**

- `200 OK` on success

```json
{
    "services": [
        {
            "name": "ZeroConf Service Discovery API at Frantiseks-MacBook-Pro",
            "hostName": "Frantiseks-MacBook-Pro.local.",
            "domainName": "local",
            "addresses": {
                "ipv4": [
                    "192.168.0.19"
                ],
                "ipv6": [
                    "fe80::1cb5:b8:f032:58d3%en0"
                ]
            },
            "service": {
                "type": "_http._tcp.local.",
                "port": 15051,
                "txtRecord": {
                    "get": "/a1/xploretv/v1/zeroconf"
                }
            }
        }
    ]
}
```
### Register a service

`POST /zeroconf`
```json
{
     "name": "New test service._http._tcp.local.",
     "replaceWildcards": false,
     "serviceProtocol": "any",
     "protocol": "_http._tcp.local.",
     "port": 7790
}

```
**Response**

- `201 created` on successful register 

### Unregister service
`DELETE /zeroconf/<id>`

**Response**

- `204 Unregistered` 
- `404 Service not found` 

## Troubleshooting


