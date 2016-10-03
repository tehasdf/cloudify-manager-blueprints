#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


CONSUL_SERVICE_NAME = 'consul'
ctx_properties = utils.ctx_factory.get(CONSUL_SERVICE_NAME)


def configure_consul(cluster_ips):
    if cluster_ips:
        config = _make_bootstrap_consul_config()
    else:
        config = _make_join_consul_config(cluster_ips)

    utils.write_to_json_file(config, '/etc/consul.d/config.json')
    utils.systemd.configure(CONSUL_SERVICE_NAME)


def _make_bootstrap_consul_config():
    config = _make_common_consul_config()
    config['bootstrap'] = True
    return config


def _make_join_consul_config(cluster_ips):
    config = _make_common_consul_config()
    config.update(bootstrap=False, retry_join=cluster_ips)
    return config


def _make_common_consul_config():
    return {
        'rejoin_after_leave': True,
        'server': True,
        'ui': True,
        'advertise_addr': ctx.instance.host_ip,
        'client_addr': '0.0.0.0',
        'data_dir': '/var/consul',
        'node_name': ctx.instance.id
    }


configure_consul(ctx_properties['consul_join'])
