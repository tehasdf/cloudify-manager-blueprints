#!/usr/bin/env python

from os.path import join, dirname
from cloudify import ctx
ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

PG_SERVICE_NAME = 'postgresql'
ctx_properties = utils.ctx_factory.create(PG_SERVICE_NAME)
PREREQS = [
    'postgresql95',
    'postgresql95-server',
    'postgresql95-libs',
    'postgresql95-contrib',
    'postgresql95-devel',

    # psycopg
    'libxslt-devel',
    'libxml2-devel',

    # stolon
    'go',
    'git',
]


def _install_postgresql():
    utils.sudo([
        'rpm',
        '-ivh',
        'http://yum.postgresql.org/9.5/redhat/rhel-7-x86_64/pgdg-centos95-9.5-2.noarch.rpm'  # NOQA
    ], ignore_failures=True)
    for package in PREREQS:
        utils.yum_install(package, PG_SERVICE_NAME)

    utils.sudo('ln -s /usr/pgsql-9.5/bin/pg_config /usr/bin/pg_config',
               ignore_failures=True)

    utils.mkdir('/var/pgdata')
    utils.chown(ctx_properties['user'], ctx_properties['user'], '/var/pgdata')
    utils.sudo([
        'git',
        'clone',
        'https://github.com/sorintlab/stolon',
        '/opt/cloudify/stolon'
    ])
    ctx.logger.info('Building stolon')
    utils.sudo(['/opt/cloudify/stolon/build'])

_install_postgresql()
