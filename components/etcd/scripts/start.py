#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


ETCD_SERVICE_NAME = 'etcd'

utils.start_service(ETCD_SERVICE_NAME)
utils.systemd.verify_alive(ETCD_SERVICE_NAME)
