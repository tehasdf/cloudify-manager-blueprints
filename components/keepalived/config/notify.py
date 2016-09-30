#!/usr/bin/env python

import sys
import json
import urllib2

instance_id = {{ ctx.instance.id }}
priority = {{ ctx.instance.runtime_properties.priority }}

request = urllib2.Request('http://127.0.0.1:8500/v1/kv/keepalived/nodes/' + instance_id,
                          data=json.dumps(dict(priority=priority, state=sys.argv[3])))
request.get_method = lambda: 'PUT'
resp = urllib2.urlopen(request)
response_data = resp.read()
