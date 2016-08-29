#!/usr/bin/env python

import os
from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


ETCD_SERVICE_NAME = 'etcd'
ctx_properties = utils.ctx_factory.create(ETCD_SERVICE_NAME)


def install_etcd():
    etcd_package = \
        utils.download_cloudify_resource(ctx_properties['etcd_package_url'],
                                         ETCD_SERVICE_NAME)
    utils.untar(etcd_package, destination='/opt/cloudify/etcd')
    utils.systemd.configure(ETCD_SERVICE_NAME)
    utils.systemd.systemctl('daemon-reload')


install_etcd()
