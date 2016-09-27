#!/usr/bin/env python2
#
# Salt unfortunately requires python 2 at thes time of writing.
#
from __future__ import print_function

import os
import sys
import logging

from . import StateLayer

_LOG = logging.getLogger(__name__)


def _logger_setup(env_var='LOG_LEVEL', default_level=logging.INFO):
    '''
    Configure logger based on env var with default level.
    '''
    log_level = os.environ.get(env_var, default_level)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s| %(name)s/%(process)d: %(message)s '
               '@%(funcName)s:%(lineno)d #%(levelname)s',
        stream=sys.stdout,
    )

    log_level = logging.getLevelName(log_level)
    _LOG.setLevel(log_level)


def main():
    '''
    Main
    '''
    if len(sys.argv) != 2:
        basename = os.path.basename(sys.argv[0])
        print("Usage: %s LAYER_PATH" % basename, file=sys.stderr)
        sys.exit(1)
    path = sys.argv[1]
    layer = StateLayer(path)
    layer.install()
    if layer.applyable:
        ret, retcode = layer.apply()
        sys.exit(retcode)


if __name__ == '__main__':
    _logger_setup()
    main()
