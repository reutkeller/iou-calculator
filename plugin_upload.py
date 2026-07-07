#!/usr/bin/env python
# coding=utf-8
"""This script uploads a plugin package to the plugin repository.
        Authors: A. Pasotti, V. Picavet
        git sha              : $TemplateVCSFormat
"""

import sys
import getpass
import base64
from optparse import OptionParser

# Use requests and defusedxml to completely avoid any xmlrpc trace
import requests
from defusedxml import minidom

# Configuration
PROTOCOL = 'https'
SERVER = 'plugins.qgis.org'
PORT = '443'
ENDPOINT = '/plugins/RPC2/'


class UploadProtocolError(Exception):
    """Custom exception for handling HTTP/API protocol mismatches."""
    pass


def main(parameters, arguments):
    """Main entry point."""
    
    url = f"{PROTOCOL}://{parameters.server}:{parameters.port}{ENDPOINT}"
    print(f"Connecting to: {PROTOCOL}://{parameters.username}:*******@{parameters.server}:{parameters.port}{ENDPOINT}")

    try:
        with open(arguments[0], 'rb') as handle:
            plugin_zip_base64 = base64.b64encode(handle.read()).decode('utf-8')

        # Construct XML-RPC payload text securely
        xml_payload = f"""<?xml version='1.0'?>
<methodCall>
<methodName>plugin.upload</methodName>
<params>
<param>
<value><base64>{plugin_zip_base64}</base64></value>
</param>
</params>
</methodCall>"""

        # Send via normal requests POST
        response = requests.post(
            url,
            data=xml_payload,
            headers={'Content-Type': 'text/xml'},
            auth=(parameters.username, parameters.password),
            timeout=30
        )

        if response.status_code != 200:
            raise UploadProtocolError(f"HTTP {response.status_code}: {response.reason}")

        # Parse securely using defusedxml
        dom = minidom.parseString(response.text)
        values = dom.getElementsByTagName('string')
        
        # Check for server-side faults in the XML response
        faults = dom.getElementsByTagName('faultCode')
        if faults:
            fault_string = dom.getElementsByTagName('string')
            error_msg = fault_string[0].firstChild.nodeValue if fault_string else "Unknown Server Fault"
            print(f"A fault occurred: {error_msg}")
            return

        # Extract values (Plugin ID and Version ID)
        plugin_id = values[0].firstChild.nodeValue if len(values) > 0 else "Unknown"
        version_id = values[1].firstChild.nodeValue if len(values) > 1 else "Unknown"

        print(f"Plugin ID: %s" % plugin_id)
        print(f"Version ID: %s" % version_id)

    except UploadProtocolError as err:
        print(f"A protocol error occurred: {err}")
    except Exception as err:
        print(f"An error occurred: {err}")


if __name__ == "__main__":
    parser = OptionParser(usage="%prog [options] plugin.zip")
    parser.add_option("-w", "--password", dest="password", help="Password for plugin site", metavar="******")
    parser.add_option("-u", "--username", dest="username", help="Username of plugin site", metavar="user")
    parser.add_option("-p", "--port", dest="port", help="Server port to connect to", metavar="80")
    parser.add_option("-s", "--server", dest="server", help="Specify server name", metavar="plugins.qgis.org")
    
    options, args = parser.parse_args()
    if len(args) != 1:
        print("Please specify zip file.\n")
        parser.print_help()
        sys.exit(1)
        
    if not options.server:
        options.server = SERVER
    if not options.port:
        options.port = PORT
    if not options.username:
        username = getpass.getuser()
        print(f"Please enter user name [{username}] :", end=' ')
        res = input()
        options.username = res if res != "" else username
    if not options.password:
        options.password = getpass.getpass()
        
    main(options, args)