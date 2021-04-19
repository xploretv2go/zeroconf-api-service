from flask import Flask, g
from flask_restful import Resource, Api, reqparse
import socket
import shelve
import markdown
import os
from flask_cors import CORS
import logging
from dotenv import load_dotenv
import re
from time import sleep

from zeroconf import IPVersion, ServiceBrowser, ServiceInfo, Zeroconf, ServiceStateChange, ZeroconfServiceTypes

load_dotenv()

# Create an instance of Flask
app = Flask(__name__)

# Create the API
api = Api(app)

# Set CORS policy
# CORS(app, resources={r"/*": {"origins": "*"}})
app.config['CORS_HEADERS'] = 'Content-Type'
CORS(app)


# Initialize shelf DB
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = shelve.open("services")
    return db

# shelf DB teardown
@app.teardown_appcontext
def teardown_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def clear_db(shelf):
    for key in shelf.keys():
        del shelf[key]
       
class ZeroConf:
    def __init__(self):
        self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only)

    @property
    def getZeroconf(self):
        return self.zeroconf


# initialize all browser related objects as global objects.
# this way they can all be initized during the startup
# instantiate global zeroconf object
zeroconfGlobal = ZeroConf()



class Collector:
    def __init__(self):
        self.infos = []
    
    def on_service_state_change(
        self, zeroconf: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange
    ) -> None:
        if state_change is ServiceStateChange.Added:
            info = zeroconf.get_service_info(service_type, name)
            if info not in self.infos:
                self.infos.append(info) 
        if state_change is ServiceStateChange.Removed:
            info = zeroconf.get_service_info(service_type, name)
            self.infos.remove(info)
        # TODO update
    


def parseIPv4Addresses(addresses):
    ipv4_list = []
    for i in range(len(addresses)):
        if (re.match('^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', addresses[i])):
            ipv4_list.append(addresses[i])

    return ipv4_list

def parseIPv6Addresses(addresses):
    ipv6_list = []
    for i in range(len(addresses)):
        if (re.match('([a-f0-9:]+:+)+[a-f0-9]+', addresses[i])):
            ipv6_list.append(addresses[i])
    
    return ipv6_list

def serviceToOutput(info, index):
    encoding = 'utf-8'
    ipv4_list = parseIPv4Addresses(info.parsed_addresses())
    ipv6_list = parseIPv6Addresses(info.parsed_addresses())

    # split by . last element is an empty space
    domain = info.server.split('.')   
    domain.reverse()

    service = {
        "id": index,
        "name": info.name,
        "hostName": info.server,
        "domainName": domain[1] + '.',
        "addresses": {
            "ipv4": ipv4_list,
            "ipv6": ipv6_list
        },
        "service": {
            "type": info.type, 
            "port": info.port,
            "txtRecord": {}
                },
        }

    properties = {}

    for key, value in info.properties.items():
        properties[key.decode(encoding)] = value.decode(encoding)
            
    service['service']['txtRecord'].update(properties)

    return service

# Define the index route and display readme on the page
@app.route("/")
def index():
    with open(os.path.dirname(app.root_path) + '/README.md') as markdown_file:

        readme_content = markdown_file.read()
        return markdown.markdown(readme_content)


collector = Collector()
services = list(ZeroconfServiceTypes.find(zc= zeroconfGlobal.getZeroconf, ip_version=IPVersion.V4Only))
services = [x if "local." in x else x + "local." for x in services]
browser = ServiceBrowser(zeroconfGlobal.getZeroconf,services, handlers=[collector.on_service_state_change])
class ServicesRoute(Resource):
    logging.basicConfig(level=logging.DEBUG) 

    def get(self):
        shelf = get_db()
        services_discovered = []
        shelf.clear()

        for info in collector.infos:
            if(info is not None):
                shelf[(info.name).lower()] = info
                services_discovered.append(serviceToOutput(info, (info.name).lower()))    


        return {'services': services_discovered}, 200

    def post(self):
        parser = reqparse.RequestParser()
        shelf = get_db()
        
        keys = list(shelf.keys())

        parser.add_argument('name', required=True, type=str)
        parser.add_argument('replaceWildcards', required=False, type=bool)
        parser.add_argument('serviceProtocol', required=False, type=str)
        parser.add_argument('service', required=True, type=dict)

        nested_service = reqparse.RequestParser()
        nested_service.add_argument('type', required=True, type=str, location='json')
        nested_service.add_argument('port', required=True, type=int, location='json')
        nested_service.add_argument('subtype', required=False, type=str, location='json')
        nested_service.add_argument('txtRecord', required=False, type=dict, location='json')

        # parse arguments into an object
        args = parser.parse_args()

        wildcard_name = args.name
        parsedType = args.service['type']
        print(args)
        for key in keys:
            if (wildcard_name == shelf[key].name):
                return {'code': 409, 'message': 'Service already registered', 'reason': 'service with the same name has already been registered', 'data': args.name}, 409

        if (args.replaceWildcards):
            wildcard_name = str(args.name).split('.')[0] + ' at ' + socket.gethostname() + '.' + parsedType
    
        if (args.service['txtRecord'] is None): 
            args.service['txtRecord'] = {}

        if (not args.name):        
            return {'code': 400, 'message': 'Bad parameter in request', 'reason': 'wrong service name', 'data': args}, 400

        if (not args.service['type']):
            return {'code': 400, 'message': 'Bad parameter in request', 'reason': 'type is missing', 'data': args}, 400
        elif (not args.service['type'].endswith('.') or len(str(args.name)) == 0):
            return {'code': 400, 'message': 'Bad parameter in request', 'reason': "wrong type format, subtype must end with '.'", 'data': args}, 400
        
        if (not (type(args.service['port']) == int)):
            return {'code': 400, 'message': 'Bad parameter in request', 'reason': 'port not set', 'data': args}, 400
 
        if args:
            new_service = ServiceInfo(
                    parsedType,
                    wildcard_name,
                    addresses=[socket.inet_aton("127.0.0.1")],
                    port=args.service['port'],
                    server=str(socket.gethostname() + '.'),
                    properties=args.service['txtRecord']
                
            )
            zeroconf = zeroconfGlobal.getZeroconf
            shelf[(wildcard_name).lower()] = new_service

            zeroconf.register_service(new_service)
            
        return {'code': 201, 'message': 'Service registered', 'data': args}, 201


class ServiceRoute(Resource):
    def get(self, identifier):
        shelf = get_db()
        identifier = identifier.lower()

        if not (identifier in shelf):
            return {'message': 'Service not found', 'service': {}}, 404

        return {'message': 'Service found', 'data': serviceToOutput(shelf[identifier], identifier)}, 200

    def delete(self, identifier):
        shelf = get_db()

        identifier = identifier.lower()
        zeroconf = zeroconfGlobal.getZeroconf

        if not (identifier in shelf):
            return {'code': 404, 'message': 'Device not found', 'data': {}}, 404

        zeroconf.unregister_service(shelf[identifier])
        del shelf[identifier]
        
        return '', 204


# Define routes
api.add_resource(ServicesRoute, '/v1/zeroconf')
api.add_resource(ServiceRoute, '/v1/zeroconf/<string:identifier>')