#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


ETCD_SERVICE_NAME = 'etcd'
ctx_properties = utils.ctx_factory.create(ETCD_SERVICE_NAME)

utils.systemd.configure(ETCD_SERVICE_NAME)
utils.systemd.systemctl('daemon-reload')
