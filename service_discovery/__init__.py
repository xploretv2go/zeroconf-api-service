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
from flask import jsonify
import netifaces

from zeroconf import (
    IPVersion,
    ServiceBrowser,
    ServiceInfo,
    Zeroconf,
    ServiceStateChange,
    ZeroconfServiceTypes,
)

load_dotenv()
iface = netifaces.gateways()["default"][netifaces.AF_INET][1]
ip_address = netifaces.ifaddresses(iface)[netifaces.AF_INET][0]["addr"]

# Create an instance of Flask
app = Flask(__name__)

# Create the API
api = Api(app)

# Set CORS policy
# CORS(app, resources={r"/*": {"origins": "*"}})
app.config["CORS_HEADERS"] = "Content-Type"
CORS(app)


# Initialize shelf DB
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = shelve.open("services")
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

    service = {
        "name": info.name.split(".")[0],
        "hostName": info.server,
        "domainName": "local",
        "addresses": {"ipv4": ipv4_list, "ipv6": ipv6_list},
        "service": {"type": info.type, "port": info.port, "txtRecord": {}},
    }

    properties = {}

    for key, value in info.properties.items():
        properties[key.decode(encoding)] = value.decode(encoding)

    service["service"]["txtRecord"].update(properties)

    return service


@app.before_first_request
def selfRegister():
    props = {"get": "/v1/zeroconf", "post": "/v1/zeroconf"}

    service = ServiceInfo(
        "_http._tcp.local.",
        "ZeroConf Service Discovery API._http._tcp.local.",
        addresses=[socket.inet_aton(ip_address)],
        port=int(os.getenv("PORT")),
        properties=props,
        server=str(socket.gethostname() + "."),
    )

    zeroconf = zeroconfGlobal.getZeroconf
    zeroconf.register_service(service)


# Define the index route and display readme on the page
@app.route("/")
def index():
    with open(os.path.dirname(app.root_path) + "/README.md") as markdown_file:

        readme_content = markdown_file.read()
        return markdown.markdown(readme_content)


collector = Collector()
services = list(
    ZeroconfServiceTypes.find(
        zc=zeroconfGlobal.getZeroconf, ip_version=IPVersion.V4Only
    )
)

# Add additional subtypes to the ones found
services.extend(
    [
        "_mqtt2go._http._tcp.local.",
        "_smb._tcp.local.",
        "_mqtt2go._sub._http._tcp.",
        "_flametouch._tcp.local.",
        "_mqtt._tcp.local.",
        "_ssh._tcp.local.",
        "_http._tcp.local.",
    ]
)

services = [x if "local." in x else x + "local." for x in services]
browser = ServiceBrowser(
    zeroconfGlobal.getZeroconf, services, handlers=[collector.on_service_state_change]
)


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
        shelf = get_db()

        keys = list(shelf.keys())

        parser.add_argument("name", required=True, type=str)
        parser.add_argument("replaceWildcards", required=False, type=bool)
        parser.add_argument("serviceProtocol", required=False, type=str)
        parser.add_argument("service", required=True, type=dict)

        nested_service = reqparse.RequestParser()
        nested_service.add_argument("type", required=True, type=str, location="json")
        nested_service.add_argument("port", required=True, type=int, location="json")
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

        if args.replaceWildcards:
            wildcard_name = (
                str(args.name).split(".")[0]
                + " at "
                + socket.gethostname()
                + "."
                + parsedType
            )

        if args:
            new_service = ServiceInfo(
                parsedType,
                wildcard_name,
                addresses=[socket.inet_aton("127.0.0.1")],
                port=args.service["port"],
                server=str(socket.gethostname() + "."),
                properties=args.service["txtRecord"],
            )
            zeroconf = zeroconfGlobal.getZeroconf
            zeroconf.register_service(new_service)
            shelf[(wildcard_name).lower()] = new_service

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
        shelf = get_db()
        keys = list(shelf.keys())

        identifier = identifier.lower()
        zeroconf = zeroconfGlobal.getZeroconf

        matching = [s for s in keys if identifier in s]

        if not matching:
            return {
                "code": 404,
                "message": "Device not found",
                "status": identifier,
            }, 404

        if not (matching[0] in shelf):
            return {
                "code": 404,
                "message": "Device not found",
                "status": identifier,
            }, 404

        service = shelf[matching[0]]

        zeroconf.unregister_service(service)
        collector.infos.remove(service)
        del shelf[matching[0]]

        return "", 204

    # delete method through post request in case of beacon usage
    def post(self, identifier):
        shelf = get_db()
        keys = list(shelf.keys())

        identifier = identifier.lower()
        zeroconf = zeroconfGlobal.getZeroconf

        matching = [s for s in keys if identifier in s]

        if not matching:
            return {
                "code": 404,
                "message": "Device not found",
                "status": identifier,
            }, 404

        if not (matching[0] in shelf):
            return {
                "code": 404,
                "message": "Device not found",
                "status": identifier,
            }, 404

        service = shelf[matching[0]]

        zeroconf.unregister_service(service)
        collector.infos.remove(service)
        del shelf[matching[0]]

        return "", 204


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

api.add_resource(ServicesRoute, "/a1/xploretv/v1/zeroconf")
api.add_resource(ServiceRoute, "/a1/xploretv/v1/zeroconf/<string:identifier>")
