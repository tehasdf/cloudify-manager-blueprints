#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


SKYDNS_SERVICE_NAME = 'skydns'
ctx_properties = utils.ctx_factory.create(SKYDNS_SERVICE_NAME)


def install_skydns():
    utils.download_cloudify_resource(ctx_properties['skydns_package_url'],
                                     destination='/opt/cloudify/skydns')
    utils.sudo('chmod +x /opt/cloudify/skydns')


install_skydns()
