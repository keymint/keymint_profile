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

import re

from .exceptions import InvalidProfile


class Profile:
    """Object representation of a profile manifest file."""

    __slots__ = [
        'profile_format',
        'name',
        'version',
        'description',
        'policies',
        'authorities',
        'string',
        'tree',
        'export',
        'filename',
    ]

    def __init__(self, *, filename=None, **kwargs):
        """
        Constructor.

        :param filename: location of keymint_policy.xml.  Necessary if
        converting ``${prefix}`` in ``<export>`` values, ``str``.
        """
        # initialize all slots with values
        for attr in self.__slots__:
            value = kwargs[attr] if attr in kwargs else None
            setattr(self, attr, value)
        self.filename = filename
        # verify that no unknown keywords are passed
        unknown = set(kwargs.keys()).difference(self.__slots__)
        if unknown:
            raise TypeError('Unknown properties: %s' % ', '.join(unknown))

    def __iter__(self):
        for slot in self.__slots__:
            yield slot

    def __str__(self):
        data = {}
        for attr in self.__slots__:
            data[attr] = getattr(self, attr)
        return str(data)

    def get_policy_type(self):
        """
        Return value of export/policy_type element, or 'unknown' if unspecified.

        :returns: profile policy type
        :rtype: str
        :raises: :exc:`InvalidProfile`
        """
        policy_type_exports = self.export.findall('policy_type')
        if len(policy_type_exports) == 1:
            return policy_type_exports[0].text
        raise InvalidProfile('Only one <policy_type> element is permitted.')

    def validate(self):
        """
        Ensure that all standards for profiles are met.

        :raises InvalidProfile: in case validation fails
        """
        errors = []
        if self.profile_format:
            if not re.match('^[1-9][0-9]*$', str(self.profile_format)):
                errors.append("The 'format' attribute of the profile must "
                              'contain a positive integer if present')

        if not self.name:
            errors.append('Profile name must not be empty')
        # Must start with a lower case alphabetic character.
        # Allow lower case alphanummeric characters and underscores in
        # keymint profiles.
        valid_profile_name_regexp = '([^/ ]+/*)+(?<!/)'
        policy_type = self.get_policy_type()
        if not policy_type.startswith('keymint'):
            # Dashes are allowed for other policy_types.
            valid_profile_name_regexp = '^[a-z][a-z0-9_-]*$'
        if not re.match(valid_profile_name_regexp, self.name):
            errors.append("Profile name '%s' does not follow naming "
                          'conventions' % self.name)

        if self.version:
            if not re.match('^[0-9]+\.[0-9_]+\.[0-9_]+$', self.version):
                errors.append("Profile version '%s' does not follow version "
                              'conventions' % self.version)

        if errors:
            raise InvalidProfile('\n'.join(errors))
