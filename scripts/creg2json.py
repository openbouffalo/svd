#!/usr/bin/env pyhon

# Copyright 2023 OpenBouffalo
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license <LICENSE-MIT
# or https://opensource.org/licenses/MIT>, at your option. This file may not be
# copied, modified, or distributed except according to those terms.

import sys

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <reg.h>")
    sys.exit(1)

import re
import json
import jsonpickle
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s",
)


class Struct:
    def __init__(self, name, line):
        self.name = name
        self.line = line
        self.registers = []

    def __repr__(self):
        return f"Struct({self.name!r})"


class Register:
    def __init__(self, name, offset, line):
        self.name = name
        self.offset = offset
        self.line = line
        self.comment = None
        self.fields = []

    def __repr__(self):
        return f"Register({self.name!r}, offset={self.offset!r}, comment={self.comment!r} fields={self.fields!r})"


class Field:
    def __init__(self, name):
        self.name = name
        self.type = None
        self.comment = None
        self.bitsize = None

    def __repr__(self):
        return f"Field({self.name!r} type={self.type!r} bitsize={self.bitsize!r} comment={self.comment!r})"


class Parser:
    def __init__(self):
        self.state = "init"
        self.log = logging.getLogger(self.__class__.__name__)
        self.struct = None
        self.register = None

    def load(self, fd):
        line_number = 0
        self.log.debug(f"Reading file `{fd.name}'")

        for line in fd:
            line_number += 1

            if self.state == "init":
                if line.startswith("struct"):
                    if self.struct is not None:
                        self.log.error(
                            f"Entered unexpected struct on line {line_number}"
                        )

                    struct_name = self._read_struct_name(line)
                    self.struct = Struct(struct_name, line_number)
                    self.log.debug(
                        f"Found struct {self.struct.name} at line {line_number}"
                    )
                    self.state = "struct"
            elif self.state == "struct":
                if re.match("^\s*/\*", line):
                    self.log.debug(f"Found comment at line {line_number}")
                    (offset, comment) = self._read_reg_comment(line)

                    self.register = Register(comment, offset, line_number)
                    self.log.debug(f"{self.register}")
                    self.struct.registers.append(self.register)
                    self.state = "post_reg_comment"
                elif line.strip().startswith("};"):
                    self.log.debug(f"Finished struct {self.struct!r}")

                    s = jsonpickle.encode(self.struct, unpicklable=False, indent=2)
                    print(s)

                    self.struct = None
                    self.state = "init"
            elif self.state == "post_reg_comment":
                if re.match("\s+union \{", line):
                    self.log.debug("Found expected union")
                    self.state = "post_reg_union_def"
                else:
                    self.log.warning(
                        f"Didn't get expected union at line {line_number}. Resetting state."
                    )
                    self.state = "struct"
            elif self.state == "post_reg_union_def":
                if re.match("\s+struct {", line):
                    self.log.debug("Found expected struct")
                    self.state = "post_reg_struct_def"
                else:
                    self.log.warning(f"Expected struct at line {line_number}")
            elif self.state == "post_reg_struct_def":
                line_stripped = line.strip()

                # Parse struct fields
                if line_stripped.startswith("uint"):
                    parsed_field = self._parse_reg_field(line)

                    if parsed_field:
                        self.register.fields.append(parsed_field)
                    else:
                        self.log.warning(f"Could not parse field at line {line_number}")
                        print(line_stripped, file=sys.stderr)

                        sys.exit(1)
                elif line_stripped.startswith("}"):
                    self.state = "post_reg_struct"
                else:
                    print(line_stripped, file=sys.stderr)
                    self.log.warning(
                        f"Unexpected post_reg_struct_def line at line {line_number}"
                    )
                    # sys.exit(1)
            elif self.state == "post_reg_struct":
                # Read the union name
                result = re.search("} (.+);", line)

                if result:
                    self.register.comment = self.register.name
                    self.register.name = result.group(1)
                    self.log.debug(f"Using register name {self.register.name}")
                    self.state = "struct"

    def _read_reg_comment(self, line):
        """Extracts the offset and message of a comment line."""
        result = re.search("\* (0x[0-9a-fA-F]+) :? (.*) \*", line)

        if result:
            return (result.group(1), result.group(2))

    def _parse_reg_field(self, line):
        """Attempts to parse the given line as a register field."""

        result = re.match(
            "(uint\d+_t)\s+(.+)\s*:\s*(\d+)\s*;\s*/\*(.+)\*", line.strip()
        )

        if result:
            field = Field(result.group(2).strip())
            field.type = result.group(1).strip()
            field.bitsize = result.group(3).strip()
            field.comment = result.group(4).strip()

            return field

    def _read_struct_name(self, line):
        """Extracts the struct name from the given line."""
        return re.match("struct (\S+) {", line).group(1)


def main():
    filename = sys.argv[1]

    if filename == "-":
        f = sys.stdin
    else:
        f = open(filename, "rt")
    parser = Parser()

    struct = parser.load(f)


if __name__ == "__main__":
    main()
