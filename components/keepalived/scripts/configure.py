#!/usr/bin/env python

import json
import urllib2
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


KEEPALIVED_SERVICE_NAME = 'keepalived'
ctx_properties = utils.ctx_factory.get(KEEPALIVED_SERVICE_NAME)


def _parse_consul_response(data):
    desc = {
        'nodes': [],
        'virtualip': None
    }
    for elem in data:
        value = json.loads(elem['Value'].decode('base64'))
        if elem['Key'].startswith('keepalived/nodes'):
            desc['nodes'].append(value)
        elif elem['Key'].startswith('keepalived/virtualip'):
            desc['master'] = value
    return desc


def _register_node(state, priority):
    utils.http_request(
        'http://127.0.0.1:8500/v1/kv/keepalived/nodes/{0}'.format(
            ctx.instance.id),
        data=json.dumps({'priority': priority, 'state': state}),
        method='PUT'
    )


def _set_virtual_ip(virtualip):
    utils.http_request(
        'http://127.0.0.1:8500/v1/kv/keepalived/virtualip',
        data=json.dumps(virtualip),
        method='PUT'
    )


def configure_keepalived():
    try:
        resp = urllib2.urlopen(
            'http://127.0.0.1:8500/v1/kv/keepalived/?recurse')
    except urllib2.HTTPError as e:
        if e.code == 404:
            data = {'virtualip': None, 'nodes': []}
        else:
            raise
    else:
        data = _parse_consul_response(json.load(resp))

    if not data['nodes']:
        priority = 100
        state = 'MASTER'
    else:
        priority = min(node['priority'] for node in data['nodes']) - 1
        state = 'BACKUP'

    if data['virtualip']:
        if ctx_properties['keepalived_floating_ip'] != data['virtualip']:
            ctx.abort_operation('Keepalived virtualip was set to {0}, '
                                'but cluster is using {1}'.format(
                                    ctx_properties['keepalived_floating_ip'],
                                    data['virtualip']))
        virtualip = data['virtualip']
    else:
        _set_virtual_ip(ctx_properties['keepalived_floating_ip'])
        virtualip = ctx_properties['keepalived_floating_ip']

    _register_node(state, priority)
    ctx.instance.runtime_properties['state'] = state
    ctx.instance.runtime_properties['virtualip'] = virtualip
    ctx.instance.runtime_properties['priority'] = priority

    utils.deploy_blueprint_resource(
        'components/keepalived/config/keepalived.conf.tmpl',
        '/etc/keepalived/keepalived.conf',
        KEEPALIVED_SERVICE_NAME
    )
    notify_path = '/opt/cloudify/keepalived/notify.py'
    utils.deploy_blueprint_resource(
        'components/keepalived/config/notify.py',
        notify_path,
        KEEPALIVED_SERVICE_NAME
    )
    utils.chmod('+x', notify_path)


configure_keepalived()
utils.systemd.configure(KEEPALIVED_SERVICE_NAME)
utils.systemd.systemctl('daemon-reload')
