# Pytdlib - Python Bindings and Client for TDLib (Telegram database library).
# Copyright (C) 2018-2019 Naji <https://github.com/i-naji>
#
# This file is part of Pytdlib for generate python types and functions from  tl file.
#
# Pytdlib is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pytdlib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Pytdlib.  If not, see <http://www.gnu.org/licenses/>.

import os
import re
import shutil

HOME = "generate/api"
DESTINATION = "pytdlib/api"
notice_path = "NOTICE"
SECTION_RE = re.compile("---(\w+)---")
COMBINATOR_RE = re.compile(r'^(\w+)\s(?:.*)=\s(\w+);$', re.MULTILINE)
ARGS_RE = re.compile("(\w+):([\w<>]+)")
DOCS_RE = re.compile(r"^//[@-]")
DOCS_RE_2 = re.compile(r"^//@description")
DOCS_RE_3 = re.compile(r"^//@class")

core_types = {'int': 'int', 'int32': 'int', 'int53': 'int', 'int64': 'int', 'long': 'int', 'double': 'float',
              'bytes': 'bytes', 'string': 'str', 'Bool': 'bool'}


class Combinator:
    def __init__(self, section: str, name: str, doc: list, args: list, return_type: str, is_class: bool = False):
        self.section = section
        self.name = name
        self.doc = doc
        self.args = args
        self.return_type = return_type
        self.is_class = is_class


def snek(s: str):
    # https://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-snake-case
    s = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', s)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s).lower()


def start():
    shutil.rmtree("{}/types/".format(DESTINATION), ignore_errors=True)
    shutil.rmtree("{}/functions/".format(DESTINATION), ignore_errors=True)

    with open('{}/source/td_api.tl'.format(HOME), encoding='utf-8') as f:
            scheme = f.read()

    with open("{}/template/class.txt".format(HOME), encoding="utf-8") as f:
        template = f.read()

    with open(notice_path, encoding="utf-8") as f:
        notice = "\n".join("# {}".format(line).strip() for line in f.readlines())

    class_combinators = {}
    section = "types"
    combinators = []
    descriptions = []
    scheme_data = scheme.splitlines()

    for line in scheme_data[14:]:
        s = SECTION_RE.match(line)
        if s:
            section = "functions"
            continue

        document = DOCS_RE.match(line)
        if document:

            cls = DOCS_RE_3.match(line)
            if cls:
                class_name = line.split('@class ', 1)[1].split(' ', 1)[0]
                doc = line.split('@description ', 1)[1]
                class_combinators[class_name] = {"description": doc, "functions": []}
                continue

            start_doc = DOCS_RE_2.match(line)
            if start_doc:
                line = line.replace('description ', '', 1)

            line = line[3:]

            description = line.split('@')
            for des in description:
                descriptions.append(des)
                continue

        combinator = COMBINATOR_RE.match(line)
        if combinator:
            name, return_type = combinator.groups()
            args = ARGS_RE.findall(line)
            combinators.append(
                Combinator(
                    section,
                    name,
                    descriptions,
                    args,
                    return_type,
                )
            )

            if section == "types" and return_type in class_combinators:
                class_combinators[return_type]["functions"].append(name)

            descriptions = []

    for cls in class_combinators:
        combinators.append(
            Combinator(
                "types",
                cls,
                class_combinators[cls]["description"],
                class_combinators[cls]["functions"],
                "",
                True
            )
        )

    total = len(combinators)
    current = 0

    for c in combinators:
        print('Generating [{0:03}%] {name}'.format(
            int(current * 100 / total), name=c.name
        ), end='                                        \r', flush=True)
        current += 1

        path = "{}/{}/".format(DESTINATION, c.section)
        os.makedirs(path, exist_ok=True)
        init = "{}/__init__.py".format(path)

        if not os.path.exists(init):
            with open(init, "w", encoding="utf-8") as f:
                f.write(notice + "\n\n")

        with open(init, "a", encoding="utf-8") as f:
            f.write("from .{} import {}\n".format(snek(c.name), c.name))

        doc_args = []
        read_args = []
        fields = []

        extra, has_extra = (", extra=None", "self.extra = extra") if c.section == "types" else ("", "")

        if c.is_class:
            doc_args = c.doc + "\n\n    No parameters required."

            read_args = "\n        ".join([
                'if q["@type"] == "{0}":\n            return {0}.read(q)'.format(i)
                for i in c.args
            ])

            arguments = ""
            fields = "pass"
            return_arguments = ""
            return_read = "class"

        else:

            for i, arg in enumerate(c.args):
                arg_name, arg_type = arg

                if arg_type in core_types:
                    field_type = core_types[arg_type]
                    arg_type = "(:obj:`{}`)".format(core_types[arg_type])
                    arg_read = "q['{}']".format(arg_name)

                elif arg_type.startswith("vector"):
                    sub_type = arg_type.split("<", 1)[1][:-1]

                    if sub_type.startswith("vector"):
                        sub_type = sub_type.split("<", 1)[1][:-1]
                        if sub_type in core_types:
                            arg_type = "(List of List of :obj:`{}`)".format(core_types[sub_type])
                            field_type = "list of List of {}".format(core_types[sub_type])
                            arg_read = "q['{}']".format(arg_name)

                        else:
                            arg_type = "(List of List of :class:`pytdlib.api.types.{}`)".format(sub_type)
                            field_type = "list of list({})".format(sub_type)
                            arg_read = "[[Object.read(v) for v in i] for i in q['{}']]".format(arg_name)
                    else:
                        if sub_type in core_types:
                            arg_type = "(List of :obj:`{}`)".format(core_types[sub_type])
                            field_type = "list of {}".format(core_types[sub_type])
                            arg_read = "q['{}']".format(arg_name)

                        else:
                            arg_type = "(List of :class:`pytdlib.api.types.{}`)".format(sub_type)
                            field_type = "list of {}".format(sub_type)
                            arg_read = "[Object.read(i) for i in q['{}']]".format(arg_name)

                else:
                    arg_read = "\"{0}\" in q and Object.read(q['{0}']) or \"\"".format(arg_name)
                    field_type = arg_type
                    arg_type = "(:class:`pytdlib.api.types.{}`)".format(arg_type)

                doc_args.append(
                    "{} {}".format(
                        arg_name, arg_type,
                    )
                )

                fields.append(
                    "self.{0} = {0}  # {1}".format(arg_name, field_type)
                )

                read_args.append(
                    "{} = {}".format(
                        arg_name.upper() if arg_name == c.name else arg_name, arg_read,
                    )
                )

            if doc_args:
                doc_args = "Args:\n        " + "\n        ".join(
                    "{}:\n            {}".format(
                        doc_args[i],
                        "".join(
                            darg[1:] if darg.startswith(' ') else darg
                            for darg in c.doc[i + 1].split(' ', 1)[1].split('.'))
                    ) for i in range(len(doc_args)))
                read_args = "\n        ".join(read_args)
            else:
                doc_args = "No parameters required."
                read_args = ""

            doc_args = c.doc[0] + "\n\n    Attributes:\n        ID (:obj:`str`): ``{}``\n\n    ".format(
                c.name) + doc_args
            doc_args += "\n\n    Returns:\n        " + c.return_type
            doc_args += "\n\n    Raises:\n        :class:`pytdlib.Error`"

            arguments = ", " + ", ".join(
                [i[0] for i in c.args]
            ) if c.args else ""

            fields = "\n        ".join(
                fields
            ) if fields else "pass"

            return_arguments = ", ".join(
                [i[0].upper() if i[0] == c.name else i[0] for i in c.args]
            ) if c.args else ""

            return_read = c.name

        with open("{}/{}/{}.py".format(DESTINATION, c.section, snek(c.name)), "w+", encoding="utf-8") as f:
            f.write(
                template.format(
                    notice=notice,
                    extra=extra,
                    has_extra=has_extra,
                    docstring=doc_args,
                    class_name=c.name,
                    arguments=arguments,
                    fields=fields,
                    return_read=return_read,
                    read=read_args,
                    return_arguments=return_arguments
                )
            )
    with open("{}/util/all_types.py".format(DESTINATION), "w", encoding="utf-8") as f:
        f.write(notice + "\n\n")
        f.write("types = {")

        for c in combinators:
            if c.section == "types":
                f.write("\n    \"{0}\": \"types.{1}\",".format(c.name, snek(c.name)))
        f.write("\n}\n")
    print('Generating Apis  : [100%]               ')

if '__main__' == __name__:
    HOME = "."
    DESTINATION = "../../pytdlib/api"
    notice_path = "../../NOTICE"
    start()
