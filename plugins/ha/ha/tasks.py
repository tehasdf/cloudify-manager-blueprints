
def prepare_cluster_configuration(ctx):
    for property_name in ['cluster_config', 'consul_bootstrap', 'consul_join']:
        ctx.instance.runtime_properties[property_name] = \
            ctx.node.properties[property_name]


def manager_host_config_from_cluster_config(ctx):
    cluster_config = ctx.target.instance.runtime_properties['cluster_config']
    host_config = cluster_config.pop()

    ctx.source.instance.runtime_properties.update(host_config)
    ctx.target.instance.runtime_properties['cluster_config'] = cluster_config


def consul_in_cluster(ctx):
    consul_props = ctx.source.instance.runtime_properties
    cluster_props = ctx.target.instance.runtime_properties

    if cluster_props['consul_bootstrap']:
        consul_props['bootstrap'] = True
        consul_props['join'] = []
        cluster_props['consul_bootstrap'] = False
    else:
        consul_props['join'] = cluster_props['consul_join']
        consul_props['bootstrap'] = False

    cluster_props['consul_join'] = cluster_props['consul_join'] + \
        [ctx.source.instance.host_ip]


def manager_host_from_config(ctx):
    ctx.source.instance.runtime_properties['ip'] = \
        ctx.target.instance.runtime_properties['private_ip']


def set_floating_ip(ctx):
    ctx.source.instance.runtime_properties['floating_ip'] = \
        ctx.target.node.properties['ip']


def keepalived_config_from_host(ctx):
    ctx.source.instance.runtime_properties['keepalived'] = \
        ctx.target.instance.runtime_properties['keepalived']
