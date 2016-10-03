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


SYNCTHING_SERVICE_NAME = 'syncthing'


def start_syncthing():
    utils.start_service(SYNCTHING_SERVICE_NAME)
    utils.systemd.enable(SYNCTHING_SERVICE_NAME)

    _deploy_rerender_script()
    _register_node()


def _deploy_rerender_script():
    rerender_script_path = '/opt/cloudify/syncthing/rerender.py'
    utils.deploy_blueprint_resource(
        'components/syncthing/scripts/rerender.py',
        rerender_script_path,
        SYNCTHING_SERVICE_NAME,
        render=False
    )
    utils.chmod('+x', rerender_script_path)
    utils_ha.consul_watches.append({
        'type': 'keyprefix',
        'prefix': 'syncthing/',
        'handler': '/opt/cloudify/syncthing/rerender.py'

    })


def _register_node():
    node_info = '{0},tcp://{1},{2}'.format(
        utils_ha.syncthing_api.get_id(),
        ctx.instance.host_ip,
        ctx.instance.id)
    utils_ha.consul_kv.subdir('syncthing')[ctx.instance.id] = node_info
    ctx.logger.debug('Syncthing node_info: {0}'.format(node_info))


start_syncthing()
