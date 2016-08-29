def prepare_cluster_configuration(ctx):
    ctx.instance.runtime_properties['cluster_config'] = [
        {
            'fabric_env': {
                'host_string': '10.0.1.25',
                'key_filename': '/home/asdf/projects/cloudify/vm/.vagrant/machines/default/virtualbox/private_key',  # NOQA
                'user': 'vagrant'
            }
        }
    ]


def manager_host_config_from_cluster_config(ctx):
    cluster_config = ctx.target.instance.runtime_properties['cluster_config']
    host_config = cluster_config.pop()

    ctx.source.instance.runtime_properties.update(host_config)
    ctx.target.instance.runtime_properties['cluster_config'] = cluster_config
