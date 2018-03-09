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

from ctypes import *


class SetLogPath:

    def __init__(self, tdjson: CDLL):
        self.td_set_log_file_path = tdjson.td_set_log_file_path
        self.td_set_log_file_path.restype = c_int
        self.td_set_log_file_path.argtypes = [c_char_p]

    def __call__(self, path: str):
        return self.td_set_log_file_path(path)


class SetLogSize:

    def __init__(self, tdjson: CDLL):
        self.td_set_log_max_file_size = tdjson.td_set_log_max_file_size
        self.td_set_log_max_file_size.restype = None
        self.td_set_log_max_file_size.argtypes = [c_longlong]

    def __call__(self, size: int):
        return self.td_set_log_max_file_size(size)


class SetLogLevel:

    def __init__(self, tdjson: CDLL):
        self.td_set_log_verbosity_level = tdjson.td_set_log_verbosity_level
        self.td_set_log_verbosity_level.restype = None
        self.td_set_log_verbosity_level.argtypes = [c_int]

    def __call__(self, level: int):
        return self.td_set_log_verbosity_level(level)


class SetLogErrorCallback:

    def __init__(self, tdjson: CDLL):
        self.td_set_log_fatal_error_callback = tdjson.td_set_log_fatal_error_callback
        self.fatal_error_callback_type = CFUNCTYPE(None, c_char_p)
        self.td_set_log_fatal_error_callback.restype = None
        self.td_set_log_fatal_error_callback.argtypes = [self.fatal_error_callback_type]

    def __call__(self, func: callable):
        return self.td_set_log_fatal_error_callback(self.fatal_error_callback_type(func))
