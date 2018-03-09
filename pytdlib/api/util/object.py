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

from collections import OrderedDict
from json import JSONEncoder, dumps


class Object:
    all = {}

    def to_json(self):
        return dumps(self, cls=Encoder).encode('utf-8')

    @staticmethod
    def read(q: dict, *args):
        return Object.all[q["@type"]].read(q, *args)

    def __str__(self) -> str:
        return dumps(self, cls=Encoder, indent=4)

    def __eq__(self, other) -> bool:
        return self.__dict__ == other.__dict__

    def __len__(self) -> int:
        return len(self.__str__())

    def __call__(self):
        pass


class Encoder(JSONEncoder):
    def default(self, o: object):
        content = o.__dict__
        return OrderedDict(
            [("@type", o.ID)]
            + [("@extra", i[1]) if i[0] == "extra" else i for i in content.items()]
        )
