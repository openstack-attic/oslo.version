
#    Copyright 2012 OpenStack Foundation
#    Copyright 2012-2013 Hewlett-Packard Development Company, L.P.
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

__all__ = ['VersionInfo']

"""
Utilities for consuming the version from pkg_resources.
"""
import os
import sys

try:
    import ConfigParser as configparser
except ImportError:
    import configparser

import pkg_resources


def _expand_path(p):
    """Expand tildes and convert to an absolute path."""
    return os.path.abspath(os.path.expanduser(p))


def _get_config_dirs(project=None):
    """Return a list of directories where config files may be located.

    :param project: an optional project name

    If a project is specified, the following directories are returned::

      ~/.${project}/
      ~/
      /etc/${project}/
      /etc/

    Otherwise, these directories::

      ~/
      /etc/
    """
    if project:
        cfg_dirs = [
            _expand_path(os.path.join('~', '.' + project)),
            _expand_path('~'),
            os.path.join('/etc', project),
            '/etc'
        ]
    else:
        cfg_dirs = [
            _expand_path('~'),
            '/etc'
        ]

    return cfg_dirs


def _search_dirs(dirs, basename, extension=""):
    """Search a list of directories for a given filename.

    Iterator over the supplied directories, returning the first file
    found with the supplied name and extension.

    :param dirs: a list of directories
    :param basename: the filename, e.g. 'glance-api'
    :param extension: the file extension, e.g. '.conf'
    :returns: the path to a matching file, or None
    """
    for d in dirs:
        path = os.path.join(d, '%s%s' % (basename, extension))
        if os.path.exists(path):
            return path


def _find_config_files(project=None, prog=None, extension='.conf'):
    """Return a list of default configuration files.

    :param project: an optional project name
    :param prog: the program name, defaulting to the basename of sys.argv[0]
    :param extension: the type of the config file

    We default to two config files: [${project}.conf, ${prog}.conf]

    And we look for those config files in the following directories::

      ~/.${project}/
      ~/
      /etc/${project}/
      /etc/

    We return an absolute path for (at most) one of each of the default config
    files, for the topmost directory it exists in.

    For example, if project=foo, prog=bar and /etc/foo/foo.conf, /etc/bar.conf
    and ~/.foo/bar.conf all exist, then we return ['/etc/foo/foo.conf',
    '~/.foo/bar.conf']

    If no project name is supplied, we only look for ${prog.conf}.
    """
    if prog is None:
        prog = os.path.basename(sys.argv[0])

    cfg_dirs = _get_config_dirs(project)

    config_files = []
    if project:
        config_files.append(_search_dirs(cfg_dirs, project, extension))
    config_files.append(_search_dirs(cfg_dirs, prog, extension))

    return [f for f in config_files if f]


class VersionInfo(object):

    def __init__(self, package):
        """Object that understands versioning for a package
        :param package: name of the python package, such as glance, or
                        python-glanceclient
        """
        self.package = package
        self._release = None
        self._version = None
        self._vendor = None
        self._product = None
        self._suffix = None
        self._cached_version = None
        self._provider = None
        self._loaded = False

    def __str__(self):
        """Make the VersionInfo object behave like a string."""
        return self.version

    def __repr__(self):
        """Include the name."""
        return "VersionInfo(%s:%s)" % (self.package, self.version)

    def _load_from_setup_cfg(self):
        cfg = configparser.RawConfigParser()
        cfg.read('setup.cfg')

        self._vendor = cfg.get('metadata', 'author', None)
        self._product = cfg.get('metadata', 'description', None)

    def _load_from_pkg_info(self, provider):
        import email
        pkg_info = email.message_from_string(provider.get_metadata('PKG-INFO'))
        self._vendor = pkg_info['Author']
        self._product = pkg_info['Summary']

    def _load_from_cfg_file(self, cfgfile):
        cfg = configparser.RawConfigParser()
        cfg.read(cfgfile)

        project_name = self.package
        if project_name.startswith('python-'):
            project_name = project_name[7:]

        self._vendor = cfg.get(project_name, "vendor")
        self._product = cfg.get(project_name, "product")
        self._suffix = cfg.get(project_name, "package")

    def _load_vendor_strings(self):
        """Load default and override vendor strings.

        Load default values from the project configuration. Then try loading
        override values from release config files. At the end of this,
        self.vendor, self.product and self.suffix should be directly
        consumable.
        """
        if self._loaded:
            return

        provider = self._get_provider()
        if provider:
            self._load_from_pkg_info(provider)
        else:
            self._load_from_setup_cfg()

        cfgfile = _find_config_files("release")
        if cfgfile:
            self._load_from_cfg_file(cfgfile)
        self._loaded = True

    def _get_provider(self):
        if self._provider is None:
            try:
                requirement = pkg_resources.Requirement.parse(self.package)
                self._provider = pkg_resources.get_provider(requirement)
            except pkg_resources.DistributionNotFound:
                pass
        return self._provider

    def _get_version_from_pkg_resources(self):
        """Get the version of the package from the pkg_resources record
        associated with the package.
        """
        provider = self._get_provider()
        if provider:
            return provider.version
        else:
            # The most likely cause for this is running tests in a tree
            # produced from a tarball where the package itself has not been
            # installed into anything. Revert to setup-time logic.
            try:
                from pbr import packaging
                return packaging.get_version(self.package)
            except ImportError:
                # You're killing me. We've got nothing here.
                print("Unable to import pbr, or find pkg_resources")
                print("information for %s" % self.package)
                raise

    @property
    def release(self):
        """Return the full version of the package including suffixes indicating
        VCS status.
        """
        if self._release is None:
            self._release = self._get_version_from_pkg_resources()

        return self._release

    @property
    def version(self):
        """Return the short version minus any alpha/beta tags."""
        if self._version is None:
            parts = []
            for part in self.release.split('.'):
                if part[0].isdigit():
                    parts.append(part)
                else:
                    break
            self._version = ".".join(parts)

        return self._version

    @property
    def vendor(self):
        self._load_vendor_strings()
        return self._vendor

    @property
    def product(self):
        self._load_vendor_strings()
        return self._product

    @property
    def suffix(self):
        self._load_vendor_strings()
        return self._suffix
