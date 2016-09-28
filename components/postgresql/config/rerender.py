#!/usr/bin/env python

import json
import urllib2
import tempfile
import subprocess

response = urllib2.urlopen('http://127.0.0.1:8500/v1/kv/pg/master')

data = json.load(response)
master_config = json.loads(data[0]['Value'].decode('base64'))
master_addr = master_config['addr']

with tempfile.NamedTemporaryFile(delete=False) as f:
    # XXX db name
    f.write("""
[databases]
{0}= host={1}
""".format('cloudify', master_addr))

subprocess.check_call(['systemctl', 'reload', 'cloudify-pgbouncer'])
