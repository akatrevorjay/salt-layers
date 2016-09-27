#!/usr/bin/env python2
#
# Salt unfortunately requires python 2 at thes time of writing.
#
from __future__ import print_function

import os
import sys
import yaml
import subprocess
import logging
import salt.config
import salt.client
import salt.output

_LOG = logging.getLogger(__name__)

# State layer paths
IMAGE_ROOT = os.environ['IMAGE_ROOT']
SALT_ROOT = os.path.join(IMAGE_ROOT, 'salt')
LAYER_ROOT = os.path.join(SALT_ROOT, 'layers')
STATE_ROOT = os.path.join(SALT_ROOT, 'states')
PILLAR_ROOT = os.path.join(SALT_ROOT, 'pillar')
# Ensure sane environment
assert all([os.path.isdir(x) for x in (IMAGE_ROOT, SALT_ROOT, STATE_ROOT, PILLAR_ROOT)])

DYNAMIC_PILLAR_SLS = os.path.join(PILLAR_ROOT, 'dynamic.sls')
DYNAMIC_STATE_SLS = os.path.join(STATE_ROOT, 'dynamic.sls')


def image_cleanup():
    '''
    Cleans up image; cleans apt cache and downloaded lists.
    '''
    _LOG.debug("Running image cleanup")
    subprocess.check_call(["image-cleanup"])


def touch(file_path):
    '''
    Convenience wrapper for 'touch'ing a file.
    '''
    with open(file_path, 'a'):
        os.utime(file_path, None)
    return True


class StateLayer(object):
    '''
    An individual Salt State Layer.
    The purpose of a state layer is to allow easy caching of Docker images when being built with Salt.
    '''

    def __init__(self, path):
        # No trailing slash
        if path.endswith('/'):
            path = path[:-1]

        self.given_path = path
        self.abs_path = os.path.abspath(path)

        common_prefix = os.path.commonprefix([LAYER_ROOT, self.abs_path])
        if not common_prefix == LAYER_ROOT:
            raise Exception('Path %s is not in layer root %s' % (self.abs_path, LAYER_ROOT))

        self.path = os.path.relpath(self.abs_path, LAYER_ROOT)
        # Create salt-friendly name
        self.name = self._path_to_name(self.path)

        init_sls = os.path.join(self.abs_path, 'init.sls')
        self.applyable = os.path.exists(init_sls)

    def _path_to_name(self, path):
        if path.endswith('.sls'):
            dirname, filename = os.path.split(path)
            if filename == 'init.sls':
                # init.sls is special and can just be removed
                path = dirname
            else:
                # Cut off ext
                path = os.path.splitext(path)[0]
        name = path.replace(os.path.sep, '.')
        return name

    def __repr__(self):
        return '<%s:%s>' % (
            self.__class__.__name__,
            self.name,
        )

    def install(self):
        '''
        Install state layer (link, add to includes on dynamic sls files).

        Looks in state layer looking for sls files.
        Links pillar files into PILLAR_ROOT and adds them to the dynamic pillar.
        Adds state files to the dynamic state.
        '''
        _LOG.info('Installing state layer: %s', self.name)

        start = self.abs_path
        for abs_root, dirnames, filenames in os.walk(start):
            root = os.path.relpath(abs_root, LAYER_ROOT)
            for filename in filenames:
                filepath = os.path.join(root, filename)
                if not filename.endswith('.sls'):
                    continue
                name = self._path_to_name(filepath)
                if filename == 'pillar.sls':
                    self._link_pillar_file(filepath)
                    self._add_to_sls_include(DYNAMIC_PILLAR_SLS, name)
                else:
                    self._add_to_sls_include(DYNAMIC_STATE_SLS, name)
            # Do not recurse
            break

    def _link_pillar_file(self, filepath):
        src = os.path.join(LAYER_ROOT, filepath)
        dst = os.path.join(PILLAR_ROOT, filepath)

        _LOG.info('Linking pillar file %s -> %s', src, dst)

        if os.path.exists(dst):
            # if os.path.samefile(src, dst):
            #     _LOG.debug('Already symlinked: %s -> %s', src, dst)
            #     continue
            # dst_linked_to = os.path.realpath(dst)
            # raise Exception('Destination {} points to {} (expected {})'.format(dst, dst_linked_to, src))
            _LOG.warning('Overwriting link for %s', dst)
            os.unlink(dst)

        path = os.path.dirname(dst)
        if not os.path.isdir(path):
            _LOG.info("Creating directory and parents: %s", path)
            os.makedirs(path)

        os.symlink(src, dst)

    def _add_to_sls_include(self, sls_file, name):
        '''
        Given an sls file path, it will put name within an include block.

        If the file doesn't exist it will be created.
        If the file doesn't contain an include block one will be added.
        '''
        # Create file if it does not exist.
        if not os.path.exists(sls_file):
            _LOG.info('Creating file: %s', sls_file)
            touch(sls_file)

        with open(sls_file, 'r+') as fp:
            contents = yaml.load(fp)

            if not contents:
                contents = dict(include=[])
            elif 'include' not in contents:
                contents['include'] = []

            if name in contents['include']:
                _LOG.debug('Already included %s in sls %s', name, sls_file)
                return

            _LOG.info('Adding %s as include in sls %s', name, sls_file)
            contents['include'].append(name)

            # Write new file using existing file handle
            fp.seek(0)
            yaml.dump(contents, fp)
            fp.truncate()

    def apply(self, display_output=True, force_color=True):
        '''
        Applies the State Layer.
        '''
        _LOG.info("Applying state layer: %s", self.name)

        # Create salt client instance
        caller = salt.client.Caller()
        # Set any minion options
        if force_color:
            caller.opts['force_color'] = True

        try:
            # Run minion function to apply state
            ret = caller.cmd('state.sls', self.name)
            _LOG.debug('Salt layer %s apply ret: %s', self.name, ret)

            if display_output:
                # Use salt outputter to display nicely
                salt.output.display_output({'local': ret}, 'highstate', caller.opts)

            # I hate this, but this is how it's done in salt.cli.caller
            func = caller.sminion.functions['state.sls']
            retcode = sys.modules[func.__module__].__context__.get('retcode', 0)

            return ret, retcode
        finally:
            image_cleanup()
