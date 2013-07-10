
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
        self.release = None
        self.version = None
        self.vendor = None
        self.product = None
        self.suffix = None
        self._cached_version = None
        self._provider = None
        self._loaded = False

    def __str__(self):
        """Make the VersionInfo object behave like a string."""
        return self.version_string()

    def __repr__(self):
        """Include the name."""
        return "VersionInfo(%s:%s)" % (self.package, self.version_string())

    def _load_from_setup_cfg(self):
        import d2to1.util
        parsed_cfg = d2to1.util.cfg_to_args()
        self.vendor = parsed_cfg['author']
        self.product = parsed_cfg['description']

    def _load_from_pkg_info(self, provider):
        import email
        pkg_info = email.message_from_string(provider.get_metadata('PKG-INFO'))
        self.vendor = pkg_info['Author']
        self.product = pkg_info['Summary']

    def _load_from_cfg_file(self, cfgfile):
        try:
            cfg = configparser.RawConfigParser()
            cfg.read(cfgfile)

        except Exception:
            return

        project_name = self.package
        if project_name.startswith('python-'):
            project_name = project_name[7:]

        self.vendor = cfg.get(project_name, "vendor", self.vendor)
        self.product = cfg.get(project_name, "product", self.product)
        self.suffix = cfg.get(project_name, "package", self.suffix)

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
            from pbr import packaging
            return packaging.get_version(self.package)

    def release_string(self):
        """Return the full version of the package including suffixes indicating
        VCS status.
        """
        if self.release is None:
            self.release = self._get_version_from_pkg_resources()

        return self.release

    def version_string(self):
        """Return the short version minus any alpha/beta tags."""
        if self.version is None:
            parts = []
            for part in self.release_string().split('.'):
                if part[0].isdigit():
                    parts.append(part)
                else:
                    break
            self.version = ".".join(parts)

        return self.version

    def vendor_string(self):
        self._load_vendor_strings()
        return self.vendor

    def product_string(self):
        self._load_vendor_strings()
        return self.product

    def suffix_string(self):
        self._load_vendor_strings()
        return self.suffix

    # Compatibility functions
    canonical_version_string = version_string
    version_string_with_vcs = release_string
    package_string = suffix_string

    def cached_version_string(self, prefix=""):
        """Generate an object which will expand in a string context to
        the results of version_string(). We do this so that don't
        call into pkg_resources every time we start up a program when
        passing version information into the CONF constructor, but
        rather only do the calculation when and if a version is requested
        """
        if not self._cached_version:
            self._cached_version = "%s%s" % (prefix,
                                             self.version_string())
        return self._cached_version
