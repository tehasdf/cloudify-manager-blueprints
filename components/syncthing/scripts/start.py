#!/usr/bin/env python

import json

import xml.etree.ElementTree as ET
import urllib2

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


SYNCTHING_SERVICE_NAME = 'syncthing'

utils.start_service(SYNCTHING_SERVICE_NAME)
utils.systemd.verify_alive(SYNCTHING_SERVICE_NAME)

utils.deploy_blueprint_resource(
    'components/syncthing/scripts/rerender.py',
    '/opt/cloudify/syncthing/rerender.py',
    SYNCTHING_SERVICE_NAME,
    render=False
)

utils.deploy_blueprint_resource(
    'components/syncthing/config/syncthing.toml',
    '/etc/confd/conf.d/syncthing.toml',
    SYNCTHING_SERVICE_NAME,
    render=False
)

utils.deploy_blueprint_resource(
    'components/syncthing/config/syncthings.csv.tmpl',
    '/etc/confd/templates/syncthings.csv.tmpl',
    SYNCTHING_SERVICE_NAME,
    render=False
)

utils.systemd.restart('confd')


tree = ET.parse('/root/.config/syncthing/config.xml')
apikey = tree.findall('.//gui/apikey')[0].text
headers = {'X-Api-Key': apikey}


def json_request(url, data=None, method='GET'):
    req = urllib2.Request(url, data=data, headers=headers)
    req.get_method = lambda: method
    resp = urllib2.urlopen(req)
    return json.load(resp)


status = json_request('http://127.0.0.1:8384/rest/system/status')
my_id = status['myID']

utils.sudo([
    '/opt/cloudify/etcd/etcdctl',
    'set',
    '/syncthing/{0}'.format(ctx.instance.id),
    '{0},tcp://{1},{2}'.format(my_id, ctx.instance.host_ip, ctx.instance.id)
])
