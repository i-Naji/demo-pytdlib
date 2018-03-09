# Pytdlib - Python Bindings and Client for TDLib (Telegram database library).
# Copyright (C) 2018-2019 Naji <https://github.com/i-naji>
#
# This file is part of Pytdlib.
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

import re
from importlib import import_module
from .exceptions.all import exceptions


class Error(Exception):
    """This is the base exception class for all TDLib API related errors.
    For a finer grained control, see the specific errors below.
    """
    ID = None
    CODE = None
    NAME = None
    MESSAGE = None

    def __init__(self, x: int, message: str, code: int = 520):
        super().__init__("[{} {}]: {}".format(self.CODE, self.ID or self.NAME, self.MESSAGE.format(x=message)))

        self.x = x

        # TODO: Proper log unknown errors
        if self.CODE == 520 or self.CODE != code:
            with open("unknown_errors.txt", "a", encoding="utf-8") as f:
                f.write("{}\t{}\n".format(code, message))

    @staticmethod
    def raise_it(code: int, message: str):

        if code not in exceptions:
            raise UnknownError(code, message)

        id = re.sub(r"_\d+", "_X", message)
        if id not in exceptions[code]:
            raise UnknownError(code, message, code)

        x = re.search(r"(\d+)", message)
        x = x.group(1) if x is not None else x
        raise getattr(
            import_module("pytdlib.api.errors"),
            exceptions[code][id]
        )(x, message, code=code)


class UnknownError(Error):
    """This object represents an Unknown Error, that is, an error which
    Pyrogram does not know anything about, yet.
    """
    CODE = 520
    """:obj:`int`: Error code"""
    NAME = "Unknown error"
    MESSAGE = "{x}"
