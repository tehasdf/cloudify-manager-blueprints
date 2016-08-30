#!/usr/bin/env python

from os.path import join, dirname

from cloudify import ctx

ctx.download_resource(
    join('components', 'utils.py'),
    join(dirname(__file__), 'utils.py'))
import utils  # NOQA


CONFD_SERVICE_NAME = 'confd'

utils.start_service(CONFD_SERVICE_NAME)
utils.systemd.verify_alive(CONFD_SERVICE_NAME)
