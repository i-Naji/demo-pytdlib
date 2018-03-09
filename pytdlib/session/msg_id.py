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

from threading import Lock
from time import time

class MsgId:
    last_time = 0
    offset = 0
    lock = Lock()

    def __new__(cls) -> int:
        with cls.lock:
            now = time()
            cls.offset = cls.offset + 4 if now == cls.last_time else 0
            msg_id = int(now * 2 ** 32) + cls.offset
            cls.last_time = now

            return msg_id