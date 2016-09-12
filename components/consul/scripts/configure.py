#!/usr/bin/env python

import json
import tempfile

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


consul_config = {
    'rejoin_after_leave': True,
    'server': True,
    'ui': True,
    'advertise_addr': ctx.instance.host_ip,
    'client_addr': ctx.instance.host_ip,
    'data_dir': '/var/consul',
    'node_name': ctx.instance.id
}

if ctx.instance.runtime_properties['bootstrap']:
    consul_config['bootstrap'] = True
else:
    consul_config['bootstrap'] = False
    consul_config['retry_join'] = ctx.instance.runtime_properties['join']

with tempfile.NamedTemporaryFile(delete=False) as f:
    json.dump(consul_config, f)

utils.move(f.name, '/etc/consul.d/config.json')
CONSUL_SERVICE_NAME = 'consul'
ctx_properties = utils.ctx_factory.get(CONSUL_SERVICE_NAME)

utils.systemd.configure(CONSUL_SERVICE_NAME)
utils.systemd.systemctl('daemon-reload')
