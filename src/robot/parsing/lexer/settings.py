#  Copyright 2008-2015 Nokia Networks
#  Copyright 2016-     Robot Framework Foundation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from robot.utils import normalize_whitespace

from .tokens import Token


class Settings(object):
    names = ()
    aliases = {}
    multi_use = ()
    single_value = ()
    name_and_arguments = (
        'METADATA',
        'SUITE SETUP',
        'SUITE TEARDOWN',
        'TEST SETUP',
        'TEST TEARDOWN',
        'TEST TEMPLATE',
        'SETUP',
        'TEARDOWN',
        'TEMPLATE',
        'LIBRARY',
        'RESOURCE',
        'VARIABLES'
    )

    def __init__(self):
        self.settings = {n: None for n in self.names}

    def lex(self, statement):
        setting = statement[0]
        name = self._format_name(setting.value)
        normalized = self._normalize_name(name)
        try:
            self._validate(name, normalized, statement)
        except ValueError as err:
            setting.type = Token.ERROR
            setting.error = err.args[0]
            self._lex_comment(statement[1:])
            return
        setting.type = normalized.replace(' ', '_')
        self.settings[normalized] = statement[1:]
        if normalized in self.name_and_arguments:
            self._lex_name_and_arguments(statement[1:])
        else:
            self._lex_arguments(statement[1:])

    def _format_name(self, name):
        return name

    def _normalize_name(self, name):
        name = normalize_whitespace(name).upper()
        if name in self.aliases:
            return self.aliases[name]
        return name

    def _validate(self, name, normalized, statement):
        if normalized not in self.settings:
            raise ValueError("Non-existing setting '%s'." % name)  # TODO: Hints?
        if self.settings[normalized] is not None and normalized not in self.multi_use:
            raise ValueError("Setting '%s' allowed only once. "
                             "Only the first value is used." % name)
        if normalized in self.single_value and len(statement) > 2:
            raise ValueError("Setting '%s' accepts only one value, got %s."
                             % (name, len(statement) - 1))

    def _lex_comment(self, tokens):
        for token in tokens:
            token.type = Token.COMMENT

    def _lex_name_and_arguments(self, tokens):
        if tokens:
            tokens[0].type = Token.NAME
        self._lex_arguments(tokens[1:])

    def _lex_arguments(self, tokens):
        for token in tokens:
            token.type = Token.ARGUMENT


class TestCaseFileSettings(Settings):
    names = (
        'DOCUMENTATION',
        'METADATA',
        'SUITE SETUP',
        'SUITE TEARDOWN',
        'TEST SETUP',
        'TEST TEARDOWN',
        'TEST TEMPLATE',
        'TEST TIMEOUT',
        'FORCE TAGS',
        'DEFAULT TAGS',
        'LIBRARY',
        'RESOURCE',
        'VARIABLES'
    )
    aliases = {
        'TASK SETUP': 'TEST SETUP',
        'TASK TEARDOWN': 'TEST TEARDOWN',
        'TASK TEMPLATE': 'TEST TEMPLATE',
        'TASK TIMEOUT': 'TEST TIMEOUT',
    }
    multi_use = (
        'METADATA',
        'LIBRARY',
        'RESOURCE',
        'VARIABLES'
    )
    single_value = (
        'RESOURCE',
        'TEST TIMEOUT',
        'TEST TEMPLATE'
    )


# FIXME: Implementation missing. Need to check what settings are supported.
class InitFileSettings(Settings):
    pass


class ResourceFileSettings(Settings):
    names = (
        'DOCUMENTATION',
        'LIBRARY',
        'RESOURCE',
        'VARIABLES'
    )
    multi_use = (
        'LIBRARY',
        'RESOURCE',
        'VARIABLES'
    )
    single_value = (
        'RESOURCE'
    )


class TestCaseSettings(Settings):
    names = (
        'DOCUMENTATION',
        'TAGS',
        'SETUP',
        'TEARDOWN',
        'TEMPLATE',
        'TIMEOUT'
    )
    single_value = (
        'TIMEOUT',
        'TEMPLATE'
    )

    def __init__(self, parent):
        Settings.__init__(self)
        self.parent = parent

    def _format_name(self, name):
        return name[1:-1].strip()

    @property
    def template_set(self):
        test_template = self.settings['TEMPLATE']
        if self._has_override_value(test_template):
            return False
        parent_template = self.parent.settings['TEST TEMPLATE']
        return self._has_value(test_template) or self._has_value(parent_template)

    def _has_override_value(self, template):
        if template is None:
            return False
        return template == [] or template[0].value.upper() == 'NONE'

    def _has_value(self, template):
        return template and template[0].value


class KeywordSettings(Settings):
    names = (
        'DOCUMENTATION',
        'ARGUMENTS',
        'TEARDOWN',
        'TIMEOUT',
        'TAGS',
        'RETURN'
    )
    single_value = (
        'TIMEOUT'
    )

    def _format_name(self, name):
        return name[1:-1].strip()
