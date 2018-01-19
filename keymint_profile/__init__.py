# Copyright 2014 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Library for parsing keymint_profile.xml and providing an object representation."""

# set version number
try:
    import pkg_resources
    try:
        __version__ = pkg_resources.require('keymint_profile')[0].version
    except pkg_resources.DistributionNotFound:
        __version__ = 'unset'
    finally:
        del pkg_resources
except ImportError:
    __version__ = 'unset'

import os
import shutil
from .templates import get_profile_template_path

from keymint_package.xml.defaults import set_defaults

PROFILE_MANIFEST_FILENAME = 'keymint_profile.xml'


def parse_profile(path):
    """
    Parse profile manifest.

    :param path: The path of the keymint_profile.xml file, it may or may not
    include the filename

    :returns: return :class:`Profile` instance, populated with parsed fields
    :raises: :exc:`InvalidProfile`
    :raises: :exc:`IOError`
    """
    import os

    from .exceptions import InvalidProfile

    if os.path.isfile(path):
        filename = path
    elif profile_exists_at(path):
        filename = os.path.join(path, PROFILE_MANIFEST_FILENAME)
        if not os.path.isfile(filename):
            raise IOError("Directory '%s' does not contain a '%s'" %
                          (path, PROFILE_MANIFEST_FILENAME))
    else:
        raise IOError("Path '%s' is neither a directory containing a '%s' "
                      'file nor a file' % (path, PROFILE_MANIFEST_FILENAME))

    with open(filename, 'r', encoding='utf-8') as f:
        try:
            return parse_profile_string(f.read(), path, filename=filename)
        except InvalidProfile as e:
            e.args = [
                "Invalid profile manifest '%s': %s" %
                (filename, e)]
            raise


def profile_exists_at(path):
    """
    Check that a profile exists at the given path.

    :param path: path to a profile
    :type path: str
    :returns: True if profile exists in given path, else False
    :rtype: bool
    """
    import os

    return os.path.isdir(path) and os.path.isfile(
        os.path.join(path, PROFILE_MANIFEST_FILENAME))


def bootstrap_profile(path):
    profile_template_path = get_profile_template_path('')
    shutil.copytree(profile_template_path, path)
    # print("profile_template_path: ", profile_template_path)
    # for root, dirs, files in os.walk(profile_template_path):
    #     for file in files:
    #         source_path = os.path.join(root, file)
    #         relative_path = os.path.relpath(source_path, profile_template_path)
    #         target_path = os.path.join(path, relative_path)
    #         print("source_path: ", source_path)
    #         print("relative_path: ", relative_path)
    #         print("target_path: ", target_path)
    #         print("")



def check_schema(schema, data, filename=None):
    from .exceptions import InvalidProfile
    if not schema.is_valid(data):
        try:
            schema.validate(data)
        except Exception as ex:
            if filename is not None:
                msg = "The manifest '%s' contains invalid XML:\n" % filename
            else:
                msg = 'The manifest contains invalid XML:\n'
            raise InvalidProfile(msg + str(ex))


def parse_profile_string(data, path, *, filename=None):
    """
    Parse keymint_profile.xml string contents.

    :param data: keymint_profile.xml contents, ``str``
    :param filename: full file path for debugging, ``str``
    :returns: return parsed :class:`Profile`
    :raises: :exc:`InvalidProfile`
    """
    import xmlschema
    import xml.etree.ElementTree as ElementTree

    from .profile import Profile
    from .schemas import get_profile_schema_path

    profile_xsd_path = get_profile_schema_path('keymint_profile.xsd')
    profile_schema = xmlschema.XMLSchema(profile_xsd_path)
    check_schema(profile_schema, data, filename)
    profile_tree = ElementTree.ElementTree(ElementTree.fromstring(data))

    prf = Profile(filename=filename)
    prf.string = data
    prf.tree = profile_tree

    root = profile_tree.getroot()
    # check_schema(profile_schema, root, filename)
    prf.export = root.find('export')

    # format attribute
    value = root.get('format')
    prf.profile_format = int(value)
    assert prf.profile_format > 0, \
        ("Unable to handle '{filename}' format version '{format}', please update the "
         "manifest file to at least format version 1").format(
         filename=filename,
         format=prf.profile_format)
    assert prf.profile_format in [1], \
        ("Unable to handle '{filename}' format version '{format}', please update "
         "'keymint_profile' (e.g. on Ubuntu/Debian use: sudo apt-get update && "
         'sudo apt-get install --only-upgrade python-keymint-profile)').format(
         filename=filename,
         format=prf.profile_format)

    # name
    prf.name = root.find('name').text

    policies = root.find('policies')
    if policies is not None:
        policies_xsd_path = get_profile_schema_path('policies.xsd')
        policies_schema = xmlschema.XMLSchema(policies_xsd_path)
        prf.policies = ElementTree.Element('policies')
        for policy in policies.findall('policy'):
            policy_path = os.path.join(path, policy.find('policy_path').text)
            policy_root = ElementTree.ElementTree(file=policy_path).getroot()
            if policy.find('defaults_path') is not None:
                defaults_path = os.path.join(
                    path, policy.find('defaults_path').text)
                defaults_root = ElementTree.ElementTree(file=defaults_path).getroot()
                policy_root = set_defaults(
                    policies_schema, policy_root, defaults_root)
            check_schema(policies_schema, policy_root, policy_path)
            policy_elemts = policy_root.findall('policies/policy')
            prf.policies.extend(policy_elemts)

    authorities = root.find('authorities')
    if authorities is not None:
        authorities_xsd_path = get_profile_schema_path('authorities.xsd')
        authorities_schema = xmlschema.XMLSchema(authorities_xsd_path)
        prf.authorities = ElementTree.Element('authorities')
        for authority in authorities.findall('authority'):
            authority_path = os.path.join(path, authority.find('authority_path').text)
            authority_root = ElementTree.ElementTree(file=authority_path).getroot()
            if authority.find('defaults_path') is not None:
                defaults_path = os.path.join(
                    path, authority.find('defaults_path').text)
                defaults_root = ElementTree.ElementTree(file=defaults_path).getroot()
                authority_root = set_defaults(
                    authorities_schema, authority_root, defaults_root)
            check_schema(authorities_schema, authority_root, authority_path)
            authority_elemts = authority_root.findall('authorities/authority')
            prf.authorities.extend(authority_elemts)

    # version
    prf.version = root.findtext('version')

    # description
    prf.description = root.findtext('description')

    prf.validate()

    return prf
