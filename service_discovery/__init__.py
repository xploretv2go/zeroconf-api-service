from flask import Flask, g
from flask_restful import Resource, Api, reqparse
import socket
import shelve
import os
from flask_cors import CORS
import logging
import ssl
from dotenv import load_dotenv
import re
from flask import jsonify
from flask import request
import threading
from typing import List
import asyncio
from time import sleep
import atexit
import sys
import signal

from werkzeug.serving import make_server

from zeroconf import (
    IPVersion,
    ServiceBrowser,
    Zeroconf,
    ServiceInfo,
    ServiceStateChange,
    ZeroconfServiceTypes,
)


load_dotenv()

# Create an instance of Flask
app = Flask(__name__)

# Create the API
# api = Api(app)

types_list = []

# Returns local I{}
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


# Initialize shelf DB
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = shelve.open("discovered")
    return db


# Initialize shelf Services
def get_service_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = shelve.open("services")
    return db


# Initialize types shelf DB
def get_types_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = shelve.open("types")
    return db


# shelf DB teardown
@app.teardown_appcontext
def teardown_db(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def clear_db(shelf):
    for key in shelf.keys():
        del shelf[key]


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Origin', 'https://tv.gustostops.com')
    response.headers.add('Access-Control-Expose-Headers', '*')
    response.headers.add('Access-Control-Allow-Credentials', "true")
    response.headers.add('Access-Control-Allow-Private-Network', "true")
    return response



# Set CORS policy
#app.config["CORS_HEADERS"] = "Content-Type"

#CORS(app, resources={r"/a1/xploretv/v1/zeroconf": {"origins": "https://tv.gustostops.com",
#     "allow_headers": "*", "expose_headers": "*", "supports_credentials": False}})


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
            self,
            zeroconf: Zeroconf,
            service_type: str,
            name: str,
            state_change: ServiceStateChange,
    ) -> None:
        if state_change is ServiceStateChange.Added:
            info = zeroconf.get_service_info(service_type, name)
            if info not in self.infos:
                self.infos.append(info)
        if state_change is ServiceStateChange.Removed:
            info = zeroconf.get_service_info(service_type, name)
            if info in self.infos:
                self.infos.remove(info)


def parseIPv4Addresses(addresses):
    ipv4_list = []
    for i in range(len(addresses)):
        if re.match("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", addresses[i]):
            ipv4_list.append(addresses[i])

    return ipv4_list


def parseIPv6Addresses(addresses):
    ipv6_list = []
    for i in range(len(addresses)):
        if re.match("([a-f0-9:]+:+)+[a-f0-9]+", addresses[i]):
            ipv6_list.append(addresses[i])

    return ipv6_list


def serviceToOutput(info):
    encoding = "utf-8"
    ipv4_list = parseIPv4Addresses(info.parsed_addresses())
    ipv6_list = parseIPv6Addresses(info.parsed_addresses())

    # split by . last element is an empty space
    domain = info.server.split(".")
    domain.reverse()

    host_name = info.server

    if "local" not in domain:
        domain.insert(1, "local")
        host_name = info.server + "local."

    service = {
        "name": info.name.split(".")[0],
        "hostName": host_name,
        "domainName": "local",
        "addresses": {"ipv4": ipv4_list, "ipv6": ipv6_list},
        "service": {"type": info.type, "port": info.port, "txtRecord": {}},
    }

    properties = {}

    for key, value in info.properties.items():
        properties[key.decode(encoding)] = value.decode(encoding)

    service["service"]["txtRecord"].update(properties)

    return service


# Define the index route and display readme on the page
@app.route("/")
def index():
    shelf = get_db()
    services_discovered = []
    clear_db(shelf)

    for info in collector.infos:
        if info is not None:
            shelf[(info.name).lower()] = info
            services_discovered.append(serviceToOutput(info))

    return {"services": services_discovered}, 200


with app.app_context():
    shelf_types = get_types_db()
    services = list(
        ZeroconfServiceTypes.find(
            zc=zeroconfGlobal.getZeroconf, ip_version=IPVersion.V4Only
        )
    )
    services = [x if "local." in x else x + "local." for x in services]
    type_dict = dict.fromkeys(services, "types")

    for type in type_dict:
        shelf_types["type_dict"] = type

    types_list_tmp = dict(type_dict)
    types_list = list(types_list_tmp.keys())
    shelf_types.close()

collector = Collector()
services = list(
    ZeroconfServiceTypes.find(
        zc=zeroconfGlobal.getZeroconf, ip_version=IPVersion.V4Only
    )
)
services = [x if "local." in x else x + "local." for x in services]

# Extend service types from
services.extend(types_list)

# Add additional subtypes to the ones found
services.extend(
    [
        "_mqtt2go._http._tcp.local.",
        "_smb._tcp.local.",
        "_mqtt2go._sub._http._tcp.local.",
        "_flametouch._tcp.local.",
        "_flametouch._tcp.local.",
        "_mqtt._tcp.local.",
        "_ssh._tcp.local.",
        "_http._tcp.local.",
        "_hue._tcp.local.",
        "_hap._tcp.local.",
        "_airplay._tcp.local.",
        "_ipp._tcp.local.",
        "_privet._tcp.local.",
        "_smb._tcp.local.",
        "_afpovertcp._tcp.local.",
    ]
)

browser = ServiceBrowser(
    zeroconfGlobal.getZeroconf, services, handlers=[
        collector.on_service_state_change]
)


def selfRegister():
    props = {
        "path": "/a1/xploretv/v1/zeroconf",
        "product": "ZeroConf API-Service",
        "provider": "A1 Telekom Austria",
        "version": "1.0",
    }

    for info in collector.infos:
        print(str(info))

    hostname = socket.gethostname()
    local_ip = get_ip()

    wildcard = "ZeroConf Service Discovery API at " + hostname + "._http._tcp.local."

    service = ServiceInfo(
        "_http._tcp.local.",
        wildcard,
        addresses=[socket.inet_aton(local_ip)],
        port=int(os.getenv("PORT")),
        properties=props,
        server=str(hostname + ".local."),
    )

    print(service)
    zeroconf = zeroconfGlobal.getZeroconf
    shelf = get_service_db()

    try:
        zeroconf.register_service(service)
        shelf[wildcard.lower()] = service
    except:
        print(f"could not register service has already been registered")


class ServicesRoute(Resource):
    logging.basicConfig(level=logging.DEBUG)

    def get(self):
        shelf = get_db()
        services_discovered = []
        clear_db(shelf)

        for info in collector.infos:
            if info is not None:
                shelf[(info.name).lower()] = info
                services_discovered.append(serviceToOutput(info))

        return {"services": services_discovered}, 200

    def post(self):
        parser = reqparse.RequestParser()
        shelf = get_service_db()

        keys = list(shelf.keys())

        parser.add_argument("name", required=True, type=str)
        parser.add_argument("replaceWildcards", required=False, type=bool)
        parser.add_argument("serviceProtocol", required=False, type=str)
        parser.add_argument("service", required=True, type=dict)
        parser.add_argument("ip", required=False, type=str)

        nested_service = reqparse.RequestParser()
        nested_service.add_argument(
            "type", required=True, type=str, location="json")
        nested_service.add_argument(
            "port", required=True, type=int, location="json")
        nested_service.add_argument(
            "subtype", required=False, type=str, location="json"
        )
        nested_service.add_argument(
            "txtRecord", required=False, type=dict, location="json"
        )

        # parse arguments into an object
        args = parser.parse_args()
        parsedType = args.service["type"]

        if "subtype" in args.service:
            subtypeList = args.service["subtype"].split(".")

            if subtypeList[len(subtypeList) - 1] != "local":
                parsedType = args.service["subtype"] + ".local."

        if "type" in args.service:
            typeList = args.service["type"].split(".")

            if typeList[len(typeList) - 1] != "local" and "subtype" not in args.service:
                parsedType = args.service["type"] + ".local."

        else:
            return {
                "code": 400,
                "message": "Type missing",
                "reason": "Wrong input in the request's body",
                "status": args,
            }, 400

        if not args.name or "type" not in args.service or "port" not in args.service:
            return {
                "code": 400,
                "message": "Bad parameter in request",
                "reason": "Wrong input in the request's body",
                "status": args,
            }, 400

        if "txtRecord" in args.service:
            if args.service["txtRecord"] is None:
                args.service["txtRecord"] = {}
        elif "txtRecord" not in args.service:
            args.service["txtRecord"] = {}

        wildcard_name = (
            args.name.split(".")[0] + parsedType
            if parsedType.startswith(".")
            else args.name.split(".")[0] + "." + parsedType
        )

        if "subtype" in args.service:
            wildcard_name = (
                args.name.split(".")[0] + parsedType
                if parsedType.startswith(".")
                else args.name.split(".")[0] + "." + parsedType
            )

        for key in keys:
            if wildcard_name == shelf[key].name:
                return {
                    "code": 409,
                    "message": "Service already registered",
                    "reason": "service with the same name has already been registered",
                    "status": args.name,
                }, 409

        client_ip = request.environ['REMOTE_ADDR']
        hostname = socket.gethostbyaddr(client_ip)[0]

        if hostname == "localhost":
            hostname = socket.gethostname()
            client_ip = get_ip()

        if "ip" in args.service:
            hostname = socket.gethostbyaddr(args.service["ip"])[0]
            client_ip = args.service["ip"]

        hostname = hostname.split(".")[0]

        if args.replaceWildcards:
            wildcard_name = (
                str(args.name).split(".")[0]
                + " at "
                + hostname
                + "."
                + parsedType
            )

        if args:
            new_service = ServiceInfo(
                parsedType,
                wildcard_name,
                addresses=[socket.inet_aton(client_ip)],
                port=args.service["port"],
                properties=args.service["txtRecord"],
                server=str(hostname + ".local."),
            )

            try:
                print(new_service)
                zeroconf = zeroconfGlobal.getZeroconf
                zeroconf.register_service(new_service)
                shelf[(wildcard_name).lower()] = new_service
                args.ip = client_ip
            except:
                print(f"could not register, service has already been registered")

        return {"code": 201, "message": "Service registered", "status": args}, 201


class ServiceRoute(Resource):
    def get(self, identifier):
        shelf = get_db()
        keys = list(shelf.keys())

        identifier = identifier.lower()

        matching = [s for s in keys if identifier in s]

        if not matching:
            return {
                "code": 404,
                "message": "Device not found",
                "status": identifier,
            }, 404

        if not (matching[0] in shelf):
            return {"message": "Service not found", "service": {}}, 404

        return {
            "message": "Service found",
            "status": serviceToOutput(shelf[matching[0]]),
        }, 200

    def delete(self, identifier):
        shelf = get_service_db()
        keys = list(shelf.keys())

        identifier = identifier.lower()
        zeroconf = zeroconfGlobal.getZeroconf

        client_ip = request.environ['REMOTE_ADDR']
        hostname = socket.gethostbyaddr(client_ip)[0]

        if hostname == "localhost":
            hostname = socket.gethostname()

        matching = [s for s in keys if identifier in s]

        for m in matching:
            if hostname.split('.')[0].lower() in m:
                service = shelf[m]
                zeroconf.unregister_service(service)
                collector.infos.remove(service)
                del shelf[m]
                return "", 204

        return {
            "code": 404,
            "message": "Device not found",
            "status": identifier,
        }, 404


    # delete method through post request in case of beacon usage
    def post(self, identifier):
        shelf = get_service_db()
        keys = list(shelf.keys())

        identifier = identifier.lower()
        zeroconf = zeroconfGlobal.getZeroconf

        client_ip = request.environ['REMOTE_ADDR']
        hostname = socket.gethostbyaddr(client_ip)[0]

        if hostname == "localhost":
            hostname = socket.gethostname()

        matching = [s for s in keys if identifier in s]

        for m in matching:
            if hostname.split('.')[0].lower() in m:
                service = shelf[m]
                zeroconf.unregister_service(service)
                collector.infos.remove(service)
                del shelf[m]
                return "", 204

        return {
            "code": 404,
            "message": "Device not found",
            "status": identifier,
        }, 404


#####################
#   Error Routes
#####################


@app.errorhandler(405)
def method_not_allowed(error):
    print(error)
    return (
        jsonify(
            {
                "error": 405,
                "reason": "Method not allowed",
                "message": "request method you submitted is not known by the server",
            }
        ),
        405,
    )


@app.errorhandler(500)
def internal_server_error(error):
    print(error)
    return (
        jsonify(
            {
                "error": 500,
                "reason": "Internal server error",
                "message": "More information about this error can be found in server log",
            }
        ),
        500,
    )


#####################
#  Routes
#####################

class ServerThread(threading.Thread):

    def __init__(self, app):
        threading.Thread.__init__(self)
        self.server = make_server(os.getenv("HOST"), os.getenv("PORT"), app, ssl_context=('/etc/zeroconf-api-service/certs/fullchain.pem', '/etc/zeroconf-api-service/certs/privkey.pem'))
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        print('Starting server')
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


def start_server():
    global server
    global app
    api = Api(app)
    api.add_resource(ServicesRoute, "/a1/xploretv/v1/zeroconf")
    api.add_resource(
        ServiceRoute, "/a1/xploretv/v1/zeroconf/<string:identifier>")
    server = ServerThread(app)
    server.start()
    print('Server started')


def stop_server():
    global server
    server.shutdown()


def sigterm_handler(_signo, _stack_frame):
    sys.exit(0)


def test():
    sys.exit(0)


if __name__ == "__main__":

    atexit.register(test)
    signal.signal(signal.SIGTERM, sigterm_handler)
    signal.signal(signal.SIGINT, sigterm_handler)
    signal.signal(signal.SIGPWR, sigterm_handler)
    signal.signal(signal.SIGUSR1, sigterm_handler)

    with app.app_context():
        selfRegister()

    start_server()

    try:
        while True:
            sleep(0.1)
    except KeyboardInterrupt:
        pass
    except SystemExit:
        pass
    finally:
        print("Unregistering...")
        with app.app_context():
            for s in get_service_db().values():
                zeroconfGlobal.getZeroconf.unregister_service(s)
        stop_server()
        print('Finalized')