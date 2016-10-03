#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
ctx.download_resource(
    join('components', 'utils_ha.py'),
    join(dirname(__file__), 'utils_ha.py'))
import utils  # NOQA
import utils_ha  # NOQA


KEEPALIVED_SERVICE_NAME = 'keepalived'
ctx_properties = utils.ctx_factory.get(KEEPALIVED_SERVICE_NAME)


def configure_keepalived(keepalived_floating_ip):
    _update_keepalived_cluster_state(keepalived_floating_ip)
    _deploy_keepalived_resources()
    utils.systemd.configure(KEEPALIVED_SERVICE_NAME)


def _update_keepalived_cluster_state(keepalived_floating_ip):
    keepalived_cluster_state = utils_ha.consul_kv.subdir('keepalived')
    virtualip = keepalived_cluster_state.get('virtualip')
    nodes = keepalived_cluster_state.subdir('nodes')

    keepalived_settings = _choose_keepalived_settings(nodes)
    ctx.logger.info('Keepalived settings: {0}'.format(keepalived_settings))

    if virtualip:
        if keepalived_floating_ip != virtualip:
            ctx.abort_operation('Keepalived virtualip was set to {0}, '
                                'but cluster is using {1}'.format(
                                    keepalived_floating_ip,
                                    virtualip))
    else:
        ctx.logger.info('Keepalived cluster: no virtualip set yet, using {0}'
                        .format(keepalived_floating_ip))

        keepalived_cluster_state['virtualip'] = keepalived_floating_ip
        virtualip = keepalived_floating_ip

    nodes[ctx.instance.id] = keepalived_settings

    ctx.instance.runtime_properties.update(keepalived_settings)
    ctx.instance.runtime_properties['virtualip'] = virtualip


def _choose_keepalived_settings(nodes):
    """Choose priority and initial keepalived state based on other nodes.

    If we're the only node in the cluster, we'll be the MASTER state with
    a constant 100 priority. Otherwise, we'll be a BACKUP with the lowest
    priority.
    """
    if nodes:
        priority = 100
        state = 'MASTER'
    else:
        priority = min(node['priority'] for node in nodes.values()) - 1
        state = 'BACKUP'
    return {'priority': priority, 'state': state}


def _deploy_keepalived_resources():
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


configure_keepalived(ctx_properties['keepalived_floating_ip'])
