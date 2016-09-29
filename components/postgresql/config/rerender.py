#!/usr/bin/env python

import os
import pwd
import json
import shutil
import urllib2
import tempfile
import subprocess

response = urllib2.urlopen('http://127.0.0.1:8500/v1/kv/pg/master')

data = json.load(response)
master_config = json.loads(data[0]['Value'].decode('base64'))
master_addr = master_config['addr']

databases_path = '/etc/pgbouncer/cloudify-databases.ini'
with tempfile.NamedTemporaryFile(delete=False) as f:
    # XXX db name
    f.write("""
[databases]
{0}= host={1}
""".format('cloudify_db', master_addr))
shutil.move(f.name, databases_path)

postgres_user = pwd.getpwnam('postgres')
os.chown(databases_path, postgres_user.pw_uid, postgres_user.pw_gid)

subprocess.check_call(['systemctl', 'reload', 'cloudify-pgbouncer'])
