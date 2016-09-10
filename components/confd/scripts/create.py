#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


CONFD_SERVICE_NAME = 'confd'
ctx_properties = utils.ctx_factory.create(CONFD_SERVICE_NAME)


def install_confd():
    confd_binary = utils.download_cloudify_resource(
        ctx_properties['confd_binary_url'], CONFD_SERVICE_NAME)
    utils.move(confd_binary, '/opt/cloudify/confd/confd', rename_only=True)
    utils.mkdir('/etc/confd/conf.d')
    utils.mkdir('/etc/confd/templates')
    utils.chmod('+x', '/opt/cloudify/confd/confd')

install_confd()