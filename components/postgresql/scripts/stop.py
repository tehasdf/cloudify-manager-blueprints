#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

PS_SERVICE_NAME = 'postgresql'
REPMGRD_SERVICE_NAME = 'repmgrd'
PGBOUNCER_SERVICE_NAME = 'pgbouncer'

ctx_properties = utils.ctx_factory.get(PS_SERVICE_NAME)


for service_name in [PS_SERVICE_NAME, REPMGRD_SERVICE_NAME,
                     PGBOUNCER_SERVICE_NAME]:
    ctx.logger.info('Stopping {0}...'.format(service_name))
    utils.systemd.stop(service_name)
