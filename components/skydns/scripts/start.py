#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


SKYDNS_SERVICE_NAME = 'skydns'

utils.start_service(SKYDNS_SERVICE_NAME)
utils.systemd.verify_alive(SKYDNS_SERVICE_NAME)
