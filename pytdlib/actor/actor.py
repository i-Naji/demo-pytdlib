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


class Actor:

    def __init__(self, tdjson: CDLL):
        self.tdjson = tdjson
        self.Create = Create(self.tdjson)
        self.receive = Receive(self.tdjson)
        self.Send = Send(self.tdjson)
        self.Execute = Execute(self.tdjson)
        self.destroy = Destroy(self.tdjson)
        self.client_id = None

    def create(self):
        self.client_id = self.Create()
        self.receive.set_client_id(self.client_id)
        self.Send.set_client_id(self.client_id)
        self.Execute.set_client_id(self.client_id)
        self.destroy.set_client_id(self.client_id)


class Create:

    def __init__(self, tdjson: CDLL):
        self.td_json_client_create = tdjson.td_json_client_create
        self.td_json_client_create.restype = c_void_p
        self.td_json_client_create.argtypes = []

    def __call__(self) -> int:
        return self.td_json_client_create()


class Main:

    def __init__(self):
        self.client_id = None

    def set_client_id(self, client_id: int):
        self.client_id = client_id


class Receive(Main):

    def __init__(self, tdjson: CDLL, client_id: int = None):
        self.td_json_client_receive = tdjson.td_json_client_receive
        self.td_json_client_receive.restype = c_char_p
        self.td_json_client_receive.argtypes = [c_void_p, c_double]
        self.client_id = client_id

    def __call__(self, client_id: int = None, timeout: c_double = 1.0) -> dict:
        if client_id is not None:
            return self.td_json_client_receive(client_id, timeout)
        return self.td_json_client_receive(self.client_id, timeout)


class Send(Main):

    def __init__(self, tdjson: CDLL, client_id: int = None):
        self.td_json_client_send = tdjson.td_json_client_send
        self.td_json_client_send.restype = None
        self.td_json_client_send.argtypes = [c_void_p, c_char_p]
        self.client_id = client_id

    def __call__(self, req: str, client_id: int = None):
        if client_id is not None:
            return self.td_json_client_send(client_id, req)
        return self.td_json_client_send(self.client_id, req)


class Execute(Main):

    def __init__(self, tdjson: CDLL, client_id: int = None):
        self.td_json_client_execute = tdjson.td_json_client_execute
        self.td_json_client_execute.restype = c_char_p
        self.td_json_client_execute.argtypes = [c_void_p, c_char_p]
        self.client_id = client_id

    def __call__(self, req: str, client_id: int = None) -> bytes:
        if client_id is not None:
            return self.td_send(client_id, req)
        return self.td_json_client_execute(self.client_id, req)


class Destroy(Main):

    def __init__(self, tdjson: CDLL, client_id: int = None):
        self.td_json_client_destroy = tdjson.td_json_client_destroy
        self.td_json_client_destroy.restype = None
        self.td_json_client_destroy.argtypes = [c_void_p]
        self.client_id = client_id

    def __call__(self, client_id: int = None):
        if client_id is not None:
            return self.td_json_client_destroy(client_id, req)
        return self.td_json_client_destroy(self.client_id)
