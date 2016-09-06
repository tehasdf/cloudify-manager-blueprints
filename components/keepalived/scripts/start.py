#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


KEEPALIVED_SERVICE_NAME = 'keepalived'

utils.start_service(KEEPALIVED_SERVICE_NAME)
utils.systemd.verify_alive(KEEPALIVED_SERVICE_NAME)
