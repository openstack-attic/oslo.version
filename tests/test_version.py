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
import mock

from oslo.version import version
import tests


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


class BasicVersionTestCase(tests.BaseTestCase):

    def test_version(self):
        with mock.patch.object(version.VersionInfo,
                               '_get_version_from_pkg_resources',
                               return_value='5.5.5.5'):
            v = version.VersionInfo(None)
            self.assertEqual(v.version, '5.5.5.5')

    def test_version_and_release(self):
        with mock.patch.object(version.VersionInfo,
                               '_get_version_from_pkg_resources',
                               return_value='0.5.21.28.gae25b56'):
            v = version.VersionInfo(None)
            self.assertEqual(v.release, '0.5.21.28.gae25b56')
            self.assertEqual(v.version, '0.5.21.28')

    def test_vendor(self):
        with mock.patch.multiple(version.VersionInfo,
                                 _get_provider=mock.DEFAULT,
                                 _load_from_pkg_info=mock.DEFAULT,
                                 _load_from_setup_cfg=mock.DEFAULT):
            path = self.write_to_tempfile("""[myfoo]
vendor=bigco
product=product123
package=mysuffix
""")
            with mock.patch.object(version,
                                   '_find_config_files',
                                   return_value=path):
                v = version.VersionInfo('myfoo')
                self.assertEqual('myfoo', v.package)
                self.assertEqual('bigco', v.vendor)
                self.assertEqual('product123', v.product)
                self.assertEqual('mysuffix', v.suffix)
