#!/usr/bin/env python


from os.path import join, dirname, exists

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
ctx.download_resource(
    join('components', 'utils_ha.py'),
    join(dirname(__file__), 'utils_ha.py'))
import utils  # NOQA
import utils_ha  # NOQA

PS_SERVICE_NAME = 'postgresql'
REPMGRD_SERVICE_NAME = 'repmgrd'
PGBOUNCER_SERVICE_NAME = 'pgbouncer'


def configure_repmgr():
    postgresql_cluster_state = utils_ha.consul_kv.subdir('postgresql')
    master = postgresql_cluster_state.get('master')
    nodes = postgresql_cluster_state.subdir('nodes')

    ctx.logger.debug('Repmgr cluster nodes: '.format(nodes))
    _deploy_repmgr_config(nodes)

    node_info = _node_info()
    nodes[ctx.instance.id] = node_info

    if not master:
        ctx.logger.info('Repmgr: preparing master')
        postgresql_cluster_state['master'] = node_info
        _setup_master()
        ctx.instance.runtime_properties['initial_mode'] = 'master'
    else:
        ctx.logger.info('Repmgr: found master: {0}'.format(master))
        _setup_replica(master['address'])
        ctx.instance.runtime_properties['initial_mode'] = 'replica'

    _deploy_promote_handler()

    utils.ctx_factory.create(REPMGRD_SERVICE_NAME)
    utils.systemd.configure(REPMGRD_SERVICE_NAME)


def configure_pgbouncer():
    utils.ctx_factory.create(PGBOUNCER_SERVICE_NAME)
    utils.systemd.configure(PGBOUNCER_SERVICE_NAME)

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

    userlist_path = '/etc/pgbouncer/userlist.txt'
    with utils_ha.sudo_open(userlist_path, 'w') as f:
        f.write('"cloudify" "cloudify"\n')
    utils.chown('postgres', 'postgres', userlist_path)

    for path in ['/var/run/pgbouncer', '/var/log/pgbouncer']:
        utils.chown('postgres', 'postgres', path)

    _deploy_pgbouncer_handler()


def _deploy_repmgr_config(nodes):
    node_name = ctx.instance.id
    ctx.instance.runtime_properties['node_num'] = \
        len(nodes) + 1
    ctx.instance.runtime_properties['node_name'] = node_name

    utils.deploy_blueprint_resource(
        'components/postgresql/config/repmgr.conf',
        utils_ha.REPMGR_CONFIG,
        PS_SERVICE_NAME,
        render=True
    )
    utils.systemd.configure(PS_SERVICE_NAME)


def _setup_master():
    data_dir = ctx.node.properties['data_dir']

    if not exists(join(data_dir, 'base')):
        utils_ha.run_postgres_command(['initdb', '-D', data_dir])

    _deploy_postgresql_config(data_dir)
    _prepare_pg_hba(data_dir)

    utils.systemd.start(PS_SERVICE_NAME)

    utils_ha.run_postgres_command(['createuser', '-s', 'repmgr'])
    utils_ha.run_postgres_command(['createdb', 'repmgr', '-O', 'repmgr'])
    utils_ha.run_repmgr_command(['master', 'register'])

    utils.systemd.stop(PS_SERVICE_NAME)


def _setup_replica(master_address):
    data_dir = ctx.node.properties['data_dir']
    utils_ha.run_repmgr_command(['-U', 'repmgr', '-d', 'repmgr', '-D',
                                 data_dir, '-h', master_address, 'standby',
                                 'clone'])


def _deploy_postgresql_config(data_dir):
    postgresql_conf_path = join(data_dir, 'postgresql.conf')

    with utils_ha.sudo_open(postgresql_conf_path, 'a') as f:
        f.write("include 'postgresql.cluster.conf'")

    cluster_conf_path = join(data_dir, 'postgresql.cluster.conf')
    utils.deploy_blueprint_resource(
        'components/postgresql/config/postgresql.cluster.conf',
        cluster_conf_path,
        PS_SERVICE_NAME,
        render=True
    )
    utils.chown('postgres', 'postgres', cluster_conf_path)


def _prepare_pg_hba(data_dir):
    pg_hba_path = join(data_dir, 'pg_hba.conf')

    ctx.instance.runtime_properties['local_cidr'] = utils_ha.local_network_cidr
    utils.deploy_blueprint_resource(
        'components/postgresql/config/cluster_pg_hba.conf',
        '/tmp/cluster_pg_hba.conf',
        PS_SERVICE_NAME,
        render=True
    )
    with open('/tmp/cluster_pg_hba.conf') as f:
        cluster_pg_hba_data = f.read()

    with utils_ha.sudo_open(pg_hba_path, 'r+') as f:
        pg_hba_data = f.read()
        f.seek(0)
        f.truncate()

        f.write(cluster_pg_hba_data)
        f.write(pg_hba_data)


def _deploy_promote_handler():
    utils.deploy_blueprint_resource(
        'components/postgresql/config/promote.py',
        '/opt/cloudify/postgresql/promote.py',
        PS_SERVICE_NAME,
        render=False
    )
    utils.chmod('+x', '/opt/cloudify/postgresql/promote.py')

    node_info_path = '/opt/cloudify/postgresql/node_info.json'
    utils.write_to_json_file(_node_info(), node_info_path)
    utils.chown('postgres', 'postgres', node_info_path)


def _deploy_pgbouncer_handler():
    utils.deploy_blueprint_resource(
        'components/postgresql/config/rerender.py',
        '/opt/cloudify/postgresql/rerender.py',
        PS_SERVICE_NAME,
        render=True
    )
    utils.chmod('+x', '/opt/cloudify/postgresql/rerender.py')
    utils_ha.consul_watches.append({
        'type': 'keyprefix',
        'prefix': 'pg/master',
        'handler': '/opt/cloudify/postgresql/rerender.py'
    })


def _node_info():
    return {
        'node_num': ctx.instance.runtime_properties['node_num'],
        'node_name': ctx.instance.runtime_properties['node_name'],
        'addr': ctx.instance.host_ip
    }


configure_repmgr()
configure_pgbouncer()
