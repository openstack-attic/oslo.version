# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 Red Hat, Inc.
# Copyright 2012-2013 Hewlett-Packard Development Company, L.P.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os

import fixtures

from oslo.version import version
import tests


class DeferredVersionTestCase(tests.BaseTestCase):

    def test_cached_version(self):
        class MyVersionInfo(version.VersionInfo):
            def _get_version_from_pkg_resources(self):
                return "5.5.5.5"

        deferred_string = MyVersionInfo("openstack").\
            cached_version_string()
        self.assertEqual("5.5.5.5", deferred_string)


class FindConfigFilesTestCase(tests.BaseTestCase):

    def _monkey_patch(self, config_files):
        self.useFixture(fixtures.MonkeyPatch('sys.argv', ['foo']))
        self.useFixture(fixtures.MonkeyPatch('os.path.exists',
                        lambda p: p in config_files))

    def test_find_config_files(self):
        config_files = [os.path.expanduser('~/.blaa/blaa.conf'),
                        '/etc/foo.conf']
        self._monkey_patch(config_files)

        self.assertEqual(
            config_files, version._find_config_files(project='blaa'))

    def test_find_config_files_with_extension(self):
        config_files = ['/etc/foo.json']
        self._monkey_patch(config_files)

        self.assertEqual([], version._find_config_files(project='blaa'))
        self.assertEqual(config_files,
                         version._find_config_files(project='blaa',
                                                    extension='.json'))
