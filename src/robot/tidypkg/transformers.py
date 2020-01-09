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

from robot.parsing import Token, ModelTransformer
from robot.parsing.model.statements import EmptyLine
from robot.utils import normalize_whitespace


class PipeAdder(ModelTransformer):

    def __init__(self):
        self.indent = 0
        self.tests = []

    def visit_TestCaseSection(self, section):
        self.tests = section.body.items
        self.generic_visit(section)
        return section

    def visit_TestCase(self, node):
        self.visit_Statement(node.name_tokens)
        self.indent += 1
        self.generic_visit(node.body)
        self.indent -= 1
        return node

    def visit_Keyword(self, node):
        self.visit_Statement(node.name_tokens)
        self.indent += 1
        self.generic_visit(node.body)
        self.indent -= 1
        return node

    def visit_ForLoop(self, node):
        self.visit_Statement(node.header)
        self.indent += 1
        self.generic_visit(node.body)
        self.indent -= 1
        self.visit_Statement(node.end)
        return node

    def visit_Statement(self, statement):
        new_tokens = []
        for line in statement.lines:
            if len(line) == 1 and line[0].type == Token.EOL:
                new_tokens.extend(line)
                continue
            elif line[0].type != Token.SEPARATOR:
                line = [Token(Token.SEPARATOR, '| ')] + line
            for index, token in enumerate(line):
                if index == 0 and self.indent:
                    token.value = '|    ' * self.indent + '| '
                if index != 0 and token.type == Token.SEPARATOR:
                    token.value = ' | '
            if len(line) > 1 and line[-2].type != Token.SEPARATOR:
                line = line[:-1] + [Token(Token.SEPARATOR, ' |'), line[-1]]
            new_tokens.extend(line)
        statement.tokens = new_tokens
        return statement


class NewlineAdder(ModelTransformer):

    def __init__(self):
        self.tests = []
        self.keywords = []
        self.sections = []

    def visit_File(self, node):
        self.sections = node.sections
        self.generic_visit(node)
        return node

    def visit_Section(self, node):
        if node != self.sections[-1] and node.type != Token.COMMENT_HEADER:
            node.body.add(EmptyLine([Token(Token.EOL, '\n')]))
        return node

    def visit_TestCaseSection(self, node):
        self.tests = node.body.items
        self.generic_visit(node)
        return self.visit_Section(node)

    def visit_TestCase(self, node):
        if not node.body.items or node != self.tests[-1]:
            node.body.items.append(EmptyLine([Token(Token.EOL, '\n')]))
        return node

    def visit_KeywordSection(self, node):
        self.keywords = node.body.items
        self.generic_visit(node)
        return self.visit_Section(node)

    def visit_Keyword(self, node):
        if not node.body.items or node != self.keywords[-1]:
            node.body.items.append(EmptyLine([Token(Token.EOL, '\n')]))
        return node


class SeparatorCleaner(ModelTransformer):

    def __init__(self, separator_width):
        self.indent = 0
        self.separator = ' ' * separator_width

    def visit_TestCase(self, node):
        self.indent += 1
        self.generic_visit(node.body)
        self.indent -= 1
        return node

    def visit_Keyword(self, node):
        self.indent += 1
        self.generic_visit(node.body)
        self.indent -= 1
        return node

    def visit_ForLoop(self, node):
        self.visit_Statement(node.header)
        self.indent += 1
        self.generic_visit(node.body)
        self.indent -= 1
        self.visit_Statement(node.end)
        return node

    def visit_Statement(self, statement):
        new_tokens = []
        for line in statement.lines:
            new_tokens.extend([self.normalize_separator(i, t) for i, t in
                               enumerate(line)])
        statement.tokens = new_tokens
        self.generic_visit(statement)
        return statement

    def normalize_separator(self, index, token):
        if token.type == Token.SEPARATOR:
            if index == 0:
                token.value = self.separator * self.indent
            else:
                token.value = self.separator
        return token


class ColumnAligner(ModelTransformer):

    def __init__(self, short_test_name_length, widths):
        self.short_test_name_length = short_test_name_length
        self.widths = widths
        self.test_name_len = 0
        self.indent = 0
        self.first_statement_after_name_seen = False

    def visit_TestCase(self, node):
        self.first_statement_after_name_seen = False
        self.generic_visit(node)
        return node

    def visit_ForLoop(self, statement):
        self.indent += 1
        self.generic_visit(statement)
        self.indent -= 1
        return statement

    def visit_Statement(self, statement):
        if statement.type == Token.NAME:
            self.test_name_len = len(statement.tokens[0].value)
        elif statement.type == Token.TESTCASE_HEADER:
            self.align_header(statement)
        else:
            self.align_statement(statement)
        return statement

    def align_header(self, statement):
        for token, width in zip(statement.data_tokens[:-1], self.widths):
            token.value = token.value.ljust(width)

    def align_statement(self, statement):
        for line in statement.lines:
            line = list(filter(lambda t: t.type not in (Token.SEPARATOR, Token.EOL), line))
            line_pos = 0
            exp_pos = 0
            widths = self.widths_for_line(line)
            for token, width in zip(line, widths):
                exp_pos += width
                if self.should_write_content_after_name(line_pos):
                    exp_pos -= self.test_name_len
                    self.first_statement_after_name_seen = True
                token.value = (exp_pos - line_pos) * ' ' + token.value
                line_pos += len(token.value)

    def widths_for_line(self, line):
        if self.indent > 0 and self._should_be_indented(line):
            widths = self.widths[1:]
            widths[0] = widths[0] + self.widths[0]
            return widths
        return self.widths

    def _should_be_indented(self, line):
        return line[0].type in (Token.KEYWORD, Token.ASSIGN, Token.CONTINUATION)

    def should_write_content_after_name(self, line_pos):
        return line_pos == 0 and not self.first_statement_after_name_seen \
               and self.test_name_len < self.short_test_name_length


class ColumnWidthCounter(ModelTransformer):

    def __init__(self):
        self.widths = []

    def visit_Statement(self, statement):
        if statement.type == Token.TESTCASE_HEADER:
            self._count_widths_from_statement(statement)
        elif statement.type != Token.NAME:
            self._count_widths_from_statement(statement, indent=1)
        return statement

    def _count_widths_from_statement(self, statement, indent=0):
        for line in statement.lines:
            line = filter(lambda t: t.type not in (Token.SEPARATOR, Token.EOL), line)
            for index, token in enumerate(line, start=indent):
                if index >= len(self.widths):
                    self.widths.append(len(token.value))
                elif len(token.value) > self.widths[index]:
                    self.widths[index] = len(token.value)


class Aligner(ModelTransformer):
    setting_and_variable_name_length = 14
    short_test_name_length = 18

    def visit_TestCaseSection(self, section):
        if len(section.header.data_tokens) > 1:
            counter = ColumnWidthCounter()
            counter.visit(section)
            ColumnAligner(self.short_test_name_length,
                          counter.widths).visit(section)
        return section

    def visit_KeywordSection(self, section):
        return section

    def visit_Statement(self, statement):
        for line in statement.lines:
            # TODO: cleaner condition. Line has 2 tokens e.g. when it has
            # only name and newline
            if len(line) < 3:
                continue
            first_value = [t for t in line if t.type != Token.SEPARATOR][0]
            value_index = line.index(first_value)
            line[value_index].value = line[value_index].value.ljust(
                self.setting_and_variable_name_length)
        return statement


class Cleaner(ModelTransformer):

    def __init__(self):
        self.in_data_section = False

    def visit_Section(self, section):
        if section.type != Token.COMMENT_HEADER:
            self.in_data_section = True
        self._normalize_section_header(section)
        self.generic_visit(section)
        return section

    def _normalize_section_header(self, section):
        if section.header:
            cleaned = self._normalize(section.header[0].value, remove='*')
            section.header[0].value = '*** %s ***' % cleaned

    def _normalize(self, marker, remove=None):
        if remove:
            marker = marker.replace(remove, '')
        return normalize_whitespace(marker).strip().title()

    def visit_Statement(self, statement):
        statement.tokens = [t for t in statement.tokens if
                            t.type != Token.OLD_FOR_INDENT]
        if statement.type in Token.SETTING_TOKENS:
            self._normalize_setting_name(statement)
        self.generic_visit(statement)
        if self._is_setting_without_value(statement) or \
                self._is_empty_line_in_data(statement):
            return None
        if self.in_data_section:
            self._remove_consecutive_separators(statement)
        return statement

    def _normalize_setting_name(self, statement):
        name = statement.data_tokens[0].value
        if name.startswith('['):
            cleaned = '[%s]' % self._normalize(name[1:-1])
        else:
            cleaned = self._normalize(name)
        statement.data_tokens[0].value = cleaned

    def _is_setting_without_value(self, statement):
        return statement.type in Token.SETTING_TOKENS and \
               len(statement.data_tokens) == 1

    def _is_empty_line_in_data(self, statement):
        return self.in_data_section and statement.type == Token.EOL

    def _remove_consecutive_separators(self, statement):
        new_tokens = []
        for line in statement.lines:
            if len(line) == 1 and line[0].type == Token.EOL:
                continue
            for index, token in enumerate(line):
                prev = line[index - 1] if index > 0 else None
                if prev and token.type == prev.type == Token.SEPARATOR:
                    continue
                new_tokens.append(token)
        statement.tokens = new_tokens

    def visit_ForLoop(self, loop):
        loop.header.data_tokens[0].value = 'FOR'
        if loop.end:
            loop.end.data_tokens[0].value = 'END'
            # TODO: This can be removed when support for old style for loops
            # is removed.
            if len(loop.end.tokens) == 1:
                loop.end.tokens = (Token(Token.SEPARATOR, ''),
                                   loop.end.tokens[0], Token(Token.EOL, '\n'))
        self.generic_visit(loop)
        return loop
