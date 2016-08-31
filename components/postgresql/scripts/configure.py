#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

PG_SERVICE_NAME = 'postgresql'

for service_name in ['stolon-sentinel', 'stolon-keeper', 'stolon-proxy']:
    sid = 'cloudify-{0}'.format(service_name)
    utils.deploy_blueprint_resource(
        'components/postgresql/config/{0}.service'.format(service_name),
        "/usr/lib/systemd/system/{0}.service".format(sid),
        PG_SERVICE_NAME,
        render=True)
utils.systemd.systemctl('daemon-reload')
