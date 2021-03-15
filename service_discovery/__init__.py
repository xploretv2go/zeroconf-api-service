from ipaddress import ip_address
from flask import Flask, g
from flask.globals import session
from flask_restful import Resource, Api, reqparse
import socket
import shelve
import markdown
import os
from flask_cors import CORS
import logging
from time import sleep
from dotenv import load_dotenv
import re


from zeroconf import IPVersion, ServiceBrowser, ServiceInfo, ServiceStateChange, Zeroconf, ZeroconfServiceTypes

load_dotenv()

# Create an instance of Flask
app = Flask(__name__)

# Create the API
api = Api(app)

# Set CORS policy
CORS(app, resources={r"/*": {"origins": "*"}})

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


class ZeroConf:
    def __init__(self):
        self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only)

    @property
    def getZeroconf(self):
        return self.zeroconf

# instantiate global zeroconf object
zeroconfGlobal = ZeroConf()        

# Declare Collector object which runs the service discovery browser
class Collector:
    def __init__(self):
        self.infos = []
    
    def on_service_state_change(
        self, zeroconf: Zeroconf, service_type: str, name: str, state_change: ServiceStateChange
    ) -> None:
        if state_change is ServiceStateChange.Added:
            info = zeroconf.get_service_info(service_type, name)
            self.infos.append(info) 


def parseIPv4Addresses(addresses):
    ipv4_list = []
    for i in range(len(addresses)):
        if (re.match('^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$',addresses[i])):
            ipv4_list.append(addresses[i])
        
    return ipv4_list

def parseIPv6Addresses(addresses):
    ipv6_list = []
    for i in range(len(addresses)):
        if (re.match('([a-f0-9:]+:+)+[a-f0-9]+',addresses[i])):
            ipv6_list.append(addresses[i])
        
    return ipv6_list    

def serviceToOutput(info, index):
    encoding = 'utf-8'
    ipv4_address = info.parsed_addresses()[0] if info.parsed_addresses()[0:] else ''

    ipv4_list = parseIPv4Addresses(info.parsed_addresses())
    ipv6_list = parseIPv6Addresses(info.parsed_addresses())

    hostname = getHostnameByAddress(ipv4_address)[0] if getHostnameByAddress(ipv4_address)[0:] else '' 
    service = {
        "id": index,
        "name": info.name,
        "hostName": hostname,
        "domainName": info.server,
        "addresses": {
            "ipv4" : ipv4_list,
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

def getHostnameByAddress(addr):
     try:
        return socket.gethostbyaddr(addr)
     except socket.herror:
        return None, None, None

#@app.before_first_request
def selfRegister():
    props = {
            'get': '/v1/zeroconf',
            'post' : '/v1/zeroconf'
           }

    service = ServiceInfo(
        "_http._tcp.local.",
        "ZeroConf API._http._tcp.local.",
        addresses=[socket.inet_aton("127.0.0.1")],
        port=int(os.getenv('PORT')),
        properties=props,
        server=str(socket.gethostname() + '.'),
    )
    
    zeroconf = zeroconfGlobal.getZeroconf
    zeroconf.register_service(service)                

# Define the index route and display readme on the page
@app.route("/")
def index():
    with open(os.path.dirname(app.root_path) + '/README.md') as markdown_file:

        readme_content = markdown_file.read()

        return markdown.markdown(readme_content)


class ServicesRoute(Resource):
    logging.basicConfig(level=logging.DEBUG)

    def get(self):
        shelf = get_db()
        # keys = list(shelf.keys())

        zeroconf = zeroconfGlobal.getZeroconf
        services_discovered = []

        services = list(ZeroconfServiceTypes.find(zc= zeroconf))

        collector = Collector()
        browser = ServiceBrowser(zeroconf, services, handlers=[collector.on_service_state_change])
        sleep(1)
    

        index = 1
        for info in collector.infos:
            shelf[str(index)] = info
            services_discovered.append(serviceToOutput(info, index))    
            index += 1
            
            
        return {'services': services_discovered}, 200

    def post(self):
        parser = reqparse.RequestParser()

        parser.add_argument('name', required=False, type=str)
        parser.add_argument('replaceWildcards', required=False, type=bool)
        parser.add_argument('serviceProtocol', required=False, type=str)
        parser.add_argument('type', required=False, type=str)
        parser.add_argument('port', required=False, type=int)
        parser.add_argument('subtype', required=False, type=str)
        parser.add_argument('txtRecords', required=False, type=dict)

        # parse arguments into an object
        args = parser.parse_args()

        shelf = get_db()
        shelf[str(args.name)] = args

        #handle input exceptions before parsing the input into zeroconf service

        if str(args.serviceProtocol).lower() == 'ipv6':
                service_protocol = IPVersion.V6Only
        elif str(args.serviceProtocol).lower() == 'ipv4':
                service_protocol = IPVersion.V4Only
        else: 
             service_protocol = IPVersion.V4Only

        wildcard_name = args.name

        if (args.replaceWildcards):
            wildcard_name = str(args.name).split('.')[0] + ' at ' + socket.gethostname() + '.' + args.type

        if (args.txtRecords == None): 
                args.txtRecords = {}

        if (not args.name):        
                return {'code': 400, 'message': 'Bad parameter in request', 'reason': 'wrong service name', 'data': args}, 400

        if (not args.type):
                return {'code': 400, 'message': 'Bad parameter in request','reason': 'type is missing', 'data': args}, 400
        elif (not args.type.endswith('.') or len(str(args.name)) == 0):
                return {'code': 400, 'message': 'Bad parameter in request','reason': 'wrong type format, subtype must end with "."', 'data': args}, 400
        
        if (not (type(args.port) == int)):
                return {'code': 400, 'message': 'Bad parameter in request' ,'reason': 'port not set', 'data': args}, 400

        if (not (args.type)):
                return {'code': 400, 'message': 'Bad parameter in request' ,'reason': 'type not set', 'data': args}, 400
 
        if (args.subtype):
            if(not(args.subtype.endswith('.'))):
                args.type + args.subtype
            else: 
                return {'code': 400, 'message': 'Bad parameter in request' ,'reason': 'wrong subtype format, subtype must end with "." character' , 'data': args}, 400
    
                
        if args:
            new_service = ServiceInfo(
                    args.type,
                    wildcard_name,
                    addresses=[socket.inet_aton("127.0.0.1")],
                    port=args.port,
                    server=str(socket.gethostname() + '.'),
                    properties=args.txtRecords
                
            )
            ip_version = service_protocol
            zeroconf = Zeroconf(ip_version=ip_version)
            zeroconf.register_service(new_service)
            
        return {'code': 201, 'message': 'Service registered', 'data': args}, 201

class ServiceRoute(Resource):
    def get(self, identifier):
        shelf = get_db()

        if not (identifier in shelf):
            return {'message': 'Service not found', 'service': {}}, 404

        return {'message': 'Service found', 'data': serviceToOutput(shelf[identifier], identifier)}, 200

    def delete(self, identifier):
        shelf = get_db()
        
        zeroconf = zeroconfGlobal.getZeroconf

        if not (identifier in shelf):
            return {'code': 404, 'message': 'Device not found', 'data': {}}, 404

        zeroconf.unregister_service(shelf[identifier])
        del shelf[identifier]
        
        return {'code': 204, 'message': 'Service unregistered', 'data': identifier}, 204

class InitializeSelf(Resource):
    def post(self):
        selfRegister()

        return {'code': 201, 'message': 'ZeroConf API published as a service'}, 201


# Define routes
api.add_resource(ServicesRoute, '/v1/zeroconf')
api.add_resource(ServiceRoute, '/v1/zeroconf/<string:identifier>')

api.add_resource(InitializeSelf,'/v1/zeroconf/init')