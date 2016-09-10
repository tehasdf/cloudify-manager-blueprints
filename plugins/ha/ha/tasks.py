
def prepare_cluster_configuration(ctx):
    cluster_config = ctx.node.properties['cluster_config']
    ctx.instance.runtime_properties['manager_ips'] = \
        [h['public_ip'] for h in cluster_config]
    ctx.instance.runtime_properties['cluster_config'] = cluster_config

    if not ctx.node.properties['consul_bootstrap']:
        if not ctx.node.properties['consul_join']:
            ctx.abort_operation('no consul bootstrap or join?')
        ctx.instance.runtime_properties['consul_join'] = \
            ctx.node.properties['consul_join']
    else:
        ctx.instance.runtime_properties['consul_join'] = []


def manager_host_config_from_cluster_config(ctx):
    cluster_config = ctx.target.instance.runtime_properties['cluster_config']
    host_config = cluster_config.pop()

    ctx.source.instance.runtime_properties.update(host_config)
    ctx.target.instance.runtime_properties['cluster_config'] = cluster_config


def consul_in_cluster(ctx):
    source_props = ctx.source.instance.runtime_properties
    target_props = ctx.target.instance.runtime_properties
    join = target_props['consul_join']
    if join:
        source_props['bootstrap'] = False
        source_props['join'] = join
    else:
        source_props['bootstrap'] = True
        target_props['consul_join'] = join + [ctx.source.instance.host_ip]


def manager_host_from_config(ctx):
    ctx.source.instance.runtime_properties['ip'] = \
        ctx.target.instance.runtime_properties['private_ip']


def set_floating_ip(ctx):
    ctx.source.instance.runtime_properties['floating_ip'] = \
        ctx.target.node.properties['ip']


def keepalived_config_from_host(ctx):
    ctx.source.instance.runtime_properties['keepalived'] = \
        ctx.target.instance.runtime_properties['keepalived']
