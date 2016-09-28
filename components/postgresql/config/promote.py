#!/usr/bin/env python

import json
import urllib2
import subprocess


with open('/opt/cloudify/postgresql/node_info.json') as f:
    node_info = json.load(f)


request = urllib2.Request('http://127.0.0.1:8500/v1/kv/pg/master',
                          data=json.dumps(node_info))
request.get_method = lambda: 'PUT'
resp = urllib2.urlopen(request)
response_data = resp.read()

subprocess.check_call([
    '/usr/pgsql/bin/repmgr', 'standby', 'promote', '-f', '/etc/repmgr.conf'
])
