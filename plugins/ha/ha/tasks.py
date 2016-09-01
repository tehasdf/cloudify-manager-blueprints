import requests


def prepare_cluster_configuration(ctx):
    cluster_config = ctx.node.properties['cluster_config']
    ctx.instance.runtime_properties['manager_ips'] = \
        [v['public_ip'] for v in cluster_config]
    ctx.instance.runtime_properties['cluster_config'] = cluster_config


def manager_cluster_to_etcd_cluster(ctx):
    cluster_size = \
        len(ctx.source.node.properties['cluster_config']) + \
        len(ctx.target.node.properties['cluster_config'])
    import pudb; pu.db  # NOQA
    etcd_discovery_url = \
        'https://discovery.etcd.io/new?size={0}'.format(cluster_size)

    etcd_discovery_token = requests.get(etcd_discovery_url).text.strip()
    ctx.source.instance.runtime_properties['etcd_discovery_token'] = \
        etcd_discovery_token
    ctx.target.instance.runtime_properties['etcd_discovery_token'] = \
        etcd_discovery_token


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
