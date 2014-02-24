# Copyright 2010-2011 OpenStack Foundation
# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Common utilities used in testing"""

__all__ = [
    'BaseTestCase'
]

import os
import tempfile

import fixtures
import testresources
import testtools

_TRUE_VALUES = ('true', '1', 'yes')


class BaseTestCase(testtools.TestCase, testresources.ResourcedTestCase):

    def setUp(self):
        super(BaseTestCase, self).setUp()
        test_timeout = os.environ.get('OS_TEST_TIMEOUT', 30)
        try:
            test_timeout = int(test_timeout)
        except ValueError:
            # If timeout value is invalid, fail hard.
            print("OS_TEST_TIMEOUT set to invalid value"
                  " defaulting to no timeout")
            test_timeout = 0
        if test_timeout > 0:
            self.useFixture(fixtures.Timeout(test_timeout, gentle=True))

        if os.environ.get('OS_STDOUT_CAPTURE') in _TRUE_VALUES:
            stdout = self.useFixture(fixtures.StringStream('stdout')).stream
            self.useFixture(fixtures.MonkeyPatch('sys.stdout', stdout))
        if os.environ.get('OS_STDERR_CAPTURE') in _TRUE_VALUES:
            stderr = self.useFixture(fixtures.StringStream('stderr')).stream
            self.useFixture(fixtures.MonkeyPatch('sys.stderr', stderr))

        self.useFixture(fixtures.NestedTempfile())

    @staticmethod
    def write_to_tempfile(content, suffix='', prefix='tmp'):
        """Create temporary file or use existing file.

        This util is needed for creating temporary file with
        specified content, suffix and prefix.

        :param content: content for temporary file.
        :param suffix: same as parameter 'suffix' for mkstemp
        :param prefix: same as parameter 'prefix' for mkstemp

        For example: it can be used in database tests for creating
        configuration files.
        """
        (fd, path) = tempfile.mkstemp(suffix=suffix, prefix=prefix)
        try:
            os.write(fd, content.encode('utf-8'))
        finally:
            os.close(fd)
        return path
