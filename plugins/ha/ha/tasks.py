import requests


def prepare_cluster_configuration(ctx):
    cluster_config = [
        {
            'fabric_env': {
                'host_string': '10.0.1.25',
                'key_filename': '/home/asdf/projects/cloudify/vm/.vagrant/machines/default/virtualbox/private_key',  # NOQA
                'user': 'vagrant'
            },
            'private_ip': '10.0.1.25'
        },
        {
            'fabric_env': {
                'host_string': '10.0.1.26',
                'key_filename': '/home/asdf/projects/cloudify/vm2/.vagrant/machines/default/virtualbox/private_key',  # NOQA
                'user': 'vagrant'
            },
            'private_ip': '10.0.1.26'
        }
    ]
    ctx.instance.runtime_properties['cluster_config'] = cluster_config
    etcd_discovery_url = \
        'https://discovery.etcd.io/new?size={0}'.format(len(cluster_config))
    ctx.instance.runtime_properties['etcd_discovery_token'] = \
        requests.get(etcd_discovery_url).text.strip()


def manager_host_config_from_cluster_config(ctx):
    cluster_config = ctx.target.instance.runtime_properties['cluster_config']
    host_config = cluster_config.pop()

    ctx.source.instance.runtime_properties.update(host_config)
    ctx.target.instance.runtime_properties['cluster_config'] = cluster_config


def etcd_in_cluster(ctx):
    ctx.source.instance.runtime_properties['etcd_discovery_token'] = \
        ctx.target.instance.runtime_properties['etcd_discovery_token']


def manager_host_from_config(ctx):
    ctx.source.instance.runtime_properties['ip'] = \
        ctx.target.instance.runtime_properties['private_ip']
