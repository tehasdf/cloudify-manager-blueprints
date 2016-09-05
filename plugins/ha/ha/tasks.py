
def prepare_cluster_configuration(ctx):
    cluster_config = ctx.node.properties['cluster_config']
    ctx.instance.runtime_properties['manager_ips'] = \
        [h['public_ip'] for h in cluster_config]
    ctx.instance.runtime_properties['cluster_config'] = cluster_config


def manager_cluster_to_consul_cluster(ctx):
    consul_cluster = ctx.source.node.properties['cluster_config'] + \
        ctx.target.node.properties['cluster_config']
    cluster_size = len(consul_cluster)

    ctx.target.instance.runtime_properties['consul_cluster'] = {
        'hosts': [h['public_ip'] for h in consul_cluster],
        'expect': cluster_size
    }
    ctx.source.instance.runtime_properties['consul_cluster'] = {
        'hosts': [h['public_ip'] for h in consul_cluster],
        'expect': cluster_size
    }


def manager_host_config_from_cluster_config(ctx):
    cluster_config = ctx.target.instance.runtime_properties['cluster_config']
    host_config = cluster_config.pop()

    ctx.source.instance.runtime_properties.update(host_config)
    ctx.target.instance.runtime_properties['cluster_config'] = cluster_config


def consul_in_cluster(ctx):
    ctx.source.instance.runtime_properties['consul_cluster'] = \
        ctx.target.instance.runtime_properties['consul_cluster']


def manager_host_from_config(ctx):
    ctx.source.instance.runtime_properties['ip'] = \
        ctx.target.instance.runtime_properties['private_ip']
