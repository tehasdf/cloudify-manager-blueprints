#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

PG_SERVICE_NAME = 'postgresql'

for service_name in ['stolon-sentinel', 'stolon-keeper', 'stolon-proxy']:
    utils.start_service(service_name)


def psql(cmd):

    return utils.sudo([
        'psql',
        '--host', '127.0.0.1',
        '--port', '25432',
        '-U', 'postgres',
        '-c', cmd
    ])

psql('create database cloudify;')
psql("create user cloudify with password 'cloudify' login superuser;")
