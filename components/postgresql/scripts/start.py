#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

PG_SERVICE_NAME = 'postgresql'
ctx_properties = utils.ctx_factory.get(PG_SERVICE_NAME)


for service_name in ['stolon-sentinel', 'stolon-keeper', 'stolon-proxy']:
    utils.start_service(service_name)


def psql(cmd):
    return utils.sudo([
        'env',
        'PGPASSWORD={0}'.format(ctx_properties['pg_su_password']),
        'psql',
        '--host', '127.0.0.1',
        '--port', '25432',
        '-U', 'postgres',
        '-c', cmd
    ], ignore_failures=True)


@utils.retry(RuntimeError, tries=20)
def check_postgresql_up():
    ret = psql('select 1;')
    if ret.returncode != 0:
        raise RuntimeError('pg not running')


check_postgresql_up()

db_exists = psql("select 'exists' from pg_database where datname='cloudify';")
if 'exists' not in db_exists.aggr_stdout:
    psql('create database cloudify;')

user_exists = psql("select 'exists' from pg_user where usename='cloudify';")
if 'exists' not in user_exists.aggr_stdout:
    psql("create user cloudify with password 'cloudify' login superuser;")