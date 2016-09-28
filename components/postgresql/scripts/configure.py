#!/usr/bin/env python

import os
import json
import urllib2
import tempfile

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA

PS_SERVICE_NAME = 'postgresql'


def _node_info():
    return {
        'node_num': ctx.instance.runtime_properties['node_num'],
        'node_name': ctx.instance.runtime_properties['node_name'],
        'addr': ctx.instance.host_ip
    }


def _get_file_contents(path):
    fd, tmp_path = tempfile.mkstemp()
    os.close(fd)

    try:
        utils.copy(path, tmp_path)
        utils.chmod('a+r', tmp_path)
        with open(tmp_path) as f:
            return f.read()
    finally:
        utils.remove(tmp_path)


def _prepare_postgresql_conf(data_dir):
    postgresql_conf_path = join(data_dir, 'postgresql.conf')

    postgresql_config = _get_file_contents(postgresql_conf_path)
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(postgresql_config)
        f.write("include 'postgresql.cluster.conf'")

    utils.move(f.name, postgresql_conf_path)

    utils.deploy_blueprint_resource(
        'components/postgresql/config/postgresql.cluster.conf',
        '/tmp/postgresql.cluster.conf',
        PS_SERVICE_NAME,
        render=True
    )
    utils.move('/tmp/postgresql.cluster.conf',
               join(data_dir, 'postgresql.cluster.conf'))


def _prepare_pg_hba(data_dir):
    pg_hba_path = join(data_dir, 'pg_hba.conf')
    pg_hba_data = _get_file_contents(pg_hba_path)
    utils.deploy_blueprint_resource(
        'components/postgresql/config/cluster_pg_hba.conf',
        '/tmp/cluster_pg_hba.conf',
        PS_SERVICE_NAME,
        render=True
    )
    with open('/tmp/cluster_pg_hba.conf') as f:
        cluster_pg_hba_data = f.read()

    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(cluster_pg_hba_data)
        f.write(pg_hba_data)

    utils.move(f.name, pg_hba_path)


def setup_master():
    data_dir = ctx.node.properties['data_dir']
    ctx.instance.runtime_properties['initial_mode'] = 'master'

    data_dir = ctx.node.properties['data_dir']
    utils.run([
        'sudo', '-u', 'postgres',
        '/usr/pgsql-9.5/bin/initdb', '-D', data_dir
    ])

    _prepare_postgresql_conf(data_dir)
    _prepare_pg_hba(data_dir)

    utils.systemd.start(PS_SERVICE_NAME)

    utils.run([
        'sudo', '-u', 'postgres',
        '/usr/pgsql-9.5/bin/createuser', '-s', 'repmgr'
    ])

    utils.run([
        'sudo', '-u', 'postgres',
        '/usr/pgsql-9.5/bin/createdb', 'repmgr', '-O', 'repmgr'
    ])

    utils.run([
        'sudo', '-u', 'postgres',
        '/usr/pgsql-9.5/bin/repmgr', '-f', '/etc/repmgr.conf', 'master',
        'register'
    ])
    utils.systemd.stop(PS_SERVICE_NAME)

    node_info = _node_info()
    utils.http_request(
        'http://127.0.0.1:8500/v1/kv/pg/master'.format(node_info['node_name']),
        data=json.dumps(node_info),
        method='PUT'
    )


def setup_replica(cluster_desc):
    ctx.instance.runtime_properties['initial_mode'] = 'replica'

    data_dir = ctx.node.properties['data_dir']
    master_addr = cluster_desc['master']['addr']
    utils.run([
        'sudo', '-u', 'postgres',
        '/usr/pgsql-9.5/bin/repmgr', '-f', '/etc/repmgr.conf', '-U', 'repmgr',
        '-d', 'repmgr', '-D', data_dir, '-h', master_addr, 'standby', 'clone'
    ])


def _common_pg_config(cluster_desc):
    node_name = ctx.instance.id
    ctx.instance.runtime_properties['node_num'] = \
        len(cluster_desc['nodes']) + 1
    ctx.instance.runtime_properties['node_name'] = node_name

    utils.deploy_blueprint_resource(
        'components/postgresql/config/repmgr.conf',
        '/etc/repmgr.conf',
        PS_SERVICE_NAME,
        render=True
    )
    utils.systemd.configure(PS_SERVICE_NAME)
    utils.systemd.systemctl('daemon-reload')

    utils.http_request(
        'http://127.0.0.1:8500/v1/kv/pg/nodes/{0}'.format(node_name),
        data=json.dumps(_node_info()),
        method='PUT'
    )


def _parse_consul_response(data):
    desc = {
        'nodes': [],
        'master': None
    }
    for elem in data:
        value = json.loads(elem['Value'].decode('base64'))
        if elem['key'].startswith('pg/nodes'):
            desc['nodes'].append(value)
        elif elem['key'].startswith('pg/master'):
            desc['master'] = value
    return desc


def configure_pg():
    try:
        resp = urllib2.urlopen('http://127.0.0.1:8500/v1/kv/pg/?recurse')
    except urllib2.HTTPError as e:
        if e.code == 404:
            data = {'nodes': [], 'master': None}
        else:
            raise
    else:
        data = _parse_consul_response(json.load(resp))

    _common_pg_config(data)
    if not data['master']:
        setup_master()
    else:
        setup_replica(data)


def add_consul_watch():
    consul_pgbouncer_config = {
        'watches': [
            {
                'type': 'keyprefix',
                'prefix': 'pg/master',
                'handler': '/opt/cloudify/postgresql/rerender.py'
            }
        ]
    }
    with tempfile.NamedTemporaryFile(delete=False) as f:
        json.dump(consul_pgbouncer_config, f)
    utils.move(f.name, '/etc/consul.d/pgbouncer.json')

    utils.deploy_blueprint_resource(
        'components/postgresql/config/pgbouncer.ini',
        '/opt/cloudify/postgresql/rerender.py',
        PS_SERVICE_NAME,
        render=True
    )
    utils.chmod('+x', '/opt/cloudify/postgresql/rerender.py')


def configure_pgbouncer():
    utils.systemd.configure('pgbouncer')
    utils.systemd.systemctl('daemon-reload')
    utils.deploy_blueprint_resource(
        'components/postgresql/config/pgbouncer.ini',
        '/etc/pgbouncer/pgbouncer.ini',
        PS_SERVICE_NAME,
        render=True
    )
    utils.deploy_blueprint_resource(
        'components/postgresql/config/cloudify-databases.ini',
        '/etc/pgbouncer/cloudify-databases.ini',
        PS_SERVICE_NAME,
        render=True
    )
    # XXX md5
    utils.deploy_blueprint_resource(
        'components/postgresql/config/userlist.txt',
        '/etc/pgbouncer/userlist.txt',
        PS_SERVICE_NAME,
        render=True
    )
    for path in ['/var/run/pgbouncer', '/var/log/pgbouncer']:
        utils.chown('postgres', 'postgres', path)

    add_consul_watch()


def configure_repmgr():
    utils.deploy_blueprint_resource(
        'components/postgresql/config/promote.py',
        '/opt/cloudify/postgresql/promote.py',
        PS_SERVICE_NAME,
        render=False
    )
    utils.chmod('+x', '/opt/cloudify/postgresql/promote.py')
    # used in promote.py
    with open('/opt/cloudify/postgresql/node_info.json', 'w') as f:
        json.dump(_node_info(), f)

    utils.systemd.configure('repmgrd')
    utils.systemd.systemctl('daemon-reload')


configure_pg()
configure_repmgr()
configure_pgbouncer()
