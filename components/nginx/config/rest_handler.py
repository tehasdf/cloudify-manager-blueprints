#!/opt/manager/env/bin/python

import json
import urllib2

resp = urllib2.urlopen(
    'http://{{ ctx.source.instance.host_ip }}:8500/v1/health/service/rest?passing')

data = json.load(resp)
with open('/tmp/foo.json', 'w') as f:
    json.dump(data, f)
