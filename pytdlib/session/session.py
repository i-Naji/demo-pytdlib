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

import os
import libconf
import pytdlib
from json import loads
from queue import Queue
from ctypes import CDLL
from pathlib import Path
from .msg_id import MsgId
from pytdlib.actor import Actor
from threading import Thread, Event
from pytdlib.api.util import Object
from pytdlib.api.errors import Error
from pytdlib.api.functions import setTdlibParameters, checkDatabaseEncryptionKey


class Result:
    def __init__(self):
        self.value = None
        self.event = Event()


class Session(Actor):
    WAIT_TIMEOUT = 10
    MAX_RETRIES = 5
    WORKERS = 2
    config_name = "config"
    config_directory = "{0}/.telegram-bot".format(Path.home())
    login = False
    test_mode = False
    language_code = "en"
    use_file_db = False
    use_file_gc = True
    file_readable_names = True
    use_secret_chats = False
    use_chat_info_db = True
    use_message_db = False
    log_name = None
    verbosity = 0
    api_id = 2899
    api_hash = "36722c72256a24c1225de00eb6a1ca74"

    def __init__(self, tdjson: CDLL, profile: str = None, config: str = None):
        self.profile = profile
        self.config = config
        super(Session, self ).__init__(tdjson)

        self.load_config()

        self.default_config = True

        self.recv_queue = Queue()
        self.results = {}

        self.token_key = None
        self.phone_number = None
        self.password = None
        self.phone_code = None
        self.first_name = None
        self.last_name = None
        self.client_id = None
        self.main_workers = 0
        self.updates_queue = None
        self.recv_thread = None
        self.is_runnig = False

    def start(self, updates_queue: Queue, main_workers: int):
        self.main_workers = main_workers
        self.updates_queue = updates_queue

        self.create()

        for i in range(self.WORKERS):
            Thread(target=self.update_worker, name="UpdateWorker#{}".format(i + 1)).start()

        self.is_runnig = True

        Thread(target=self.receive_updates, name="ReceiveThread").start()

        try:
            self.send(
                setTdlibParameters(
                    Object.all["tdlibParameters"](
                        self.test_mode,
                        '{}/data'.format(self.config_directory),
                        '{}/files'.format(self.config_directory),
                        self.use_file_db,
                        self.use_chat_info_db,
                        self.use_message_db,
                        self.use_secret_chats,
                        self.api_id,
                        self.api_hash,
                        "en",
                        "Unix/Console/Bot",
                        "UNIX/??",
                        '1.1.1',
                        self.use_file_gc,
                        self.file_readable_names
                    )
                )
            )
            self.send(checkDatabaseEncryptionKey(""))
        except Exception as e:
            print(e)
            self.stop()

    def stop(self):

        self.is_runnig = False

        for _ in range(self.WORKERS):
            self.recv_queue.put(None)

        for _ in range(self.main_workers):
            self.updates_queue.put(None)

        self.destroy()

    def restart(self):
        self.stop()
        self.start(self.updates_queue, self.main_workers)

    def update_worker(self):

        while True:
            update = self.recv_queue.get()

            if update is None:
                break

            self.process_update(update)

    def process_update(self, update: bytes):
        data = loads(update.decode('utf-8'))
        msg_id = data["@extra"] if "@extra" in data else None

        if data["@type"] == "authorizationStateClosing":
            print("Closing The Client...")
        elif data["@type"] == "authorizationStateClosed":
            print("Client Closed!")
            self.stop()
        elif data["@type"] == "authorizationStateLoggingOut":
            print("Client logged out!")
            self.stop()

        data = Object.read(data)

        if msg_id in self.results:
            self.results[msg_id].value = data
            self.results[msg_id].event.set()

        if self.updates_queue is not None:
            self.updates_queue.put(data)

    def receive_updates(self):

        while True:

            if not self.is_runnig:
                break

            event = self.receive()
            if event:
                self.recv_queue.put(event)


    def _send(self, data, wait_response: bool):

        if wait_response:
            msg_id = MsgId()
            data.extra = msg_id
            self.results[msg_id] = Result()

        try:
            self.Send(data.to_json())
        except OSError:
            if wait_response:
                self.results.pop(msg_id, None)

        if wait_response:

            self.results[msg_id].event.wait(self.WAIT_TIMEOUT)
            result = self.results.pop(msg_id).value

            if result is None:
                raise TimeoutError
            elif isinstance(result, Object.all["error"]):
                Error.raise_it(result.code, result.message)
            else:
                return result

    def send(self, data, wait_response: bool = True):
        for i in range(self.MAX_RETRIES):

            try:
                return self._send(data, wait_response)
            except (OSError, TimeoutError):
                continue
        else:
            return None

    def execute(self, data):
        data =  self.Execute(data.to_json())
        data = loads(data.decode('utf-8'))
        return Object.all[data["@type"]].read(data)

    def load_config(self):
        if not self.config:
            if not os.path.exists(self.config_directory):
                os.makedirs(self.config_directory)
        else:
            self.default_config = False
            if self.config[0] == '/':
                self.config_name = os.path.basename(self.config)
                self.config_directory = os.path.dirname(self.config)
            else:
                self.config_name = self.config
        try:
            with open("{0}/{1}".format(self.config_directory, self.config_name), encoding='utf-8') as f:
                cfg = libconf.load(f)
        except FileNotFoundError:
            if self.default_config:
                print("config '{0}/{1}' not found. Using default config".format(
                    self.config_directory, self.config_name)
                )
                self.create_config()
                return
            else:
                raise IOError("can not open config file : '{0}/{1}'".format(self.config_directory, self.config_name))

        if not self.profile:
            print("no profile specified. Using default profile")
            try:
                self.profile = cfg["default_profile"]
                assert type(cfg["default_profile"]) == str
            except KeyError:
                raise KeyError("default_profile not defineded in config")
            except AttributeError:
                raise TypeError("default_profile value in config should be string")

        try:
            settings = cfg[self.profile]
            assert type(settings) == libconf.AttrDict
        except AttributeError:
            raise TypeError("{} value in config should be dict".format(self.profile))
        except KeyError:
            self.create_profile(cfg)
            return

        if "test" in settings and type(settings["test"]) == bool:
            self.test_mode = settings["test"]

        if "config_directory" in settings and type(settings["config_directory"]) == str:
            s = settings["config_directory"]
            if s[0] == "/":
                self.config_directory = s
            else:
                self.config_directory = "{0}/{1}".format(self.config_directory, s)

        # if "language_code" in settings and type(settings["language_code"]) == str:
        #    self.language_code = settings["language_code"]

        if "use_file_db" in settings and type(settings["use_file_db"]) == bool:
            self.use_file_db = settings["use_file_db"]

        if "use_file_gc" in settings and type(settings["use_file_gc"]) == bool:
            self.use_file_gc = settings["use_file_gc"]

        if "file_readable_names" in settings and type(settings["file_readable_names"]) == bool:
            self.file_readable_names = settings["file_readable_names"]

        if "use_secret_chats" in settings and type(settings["use_secret_chats"]) == bool:
            self.use_secret_chats = settings["use_secret_chats"]

        if "use_chat_info_db" in settings and type(settings["use_chat_info_db"]) == bool:
            self.use_chat_info_db = settings["use_chat_info_db"]

        if "use_message_db" in settings and type(settings["use_message_db"]) == bool:
            self.use_message_db = settings["use_message_db"]

        if "logname" in settings and type(settings["logname"]) == str:
            log = settings["logname"]
            if log[0] == "/":
                self.log_name = log
            else:
                self.log_name = "{0}/{1}".format(self.config_directory, log)

        if "verbosity" in settings and type(settings["verbosity"]) == bool:
            self.verbosity = settings["verbosity"]

        if "api_id" in settings and type(settings["api_id"]) == int and \
                "api_hash" in settings and type(settings["api_hash"]) == str:
            self.api_id = settings["api_id"]
            self.api_hash = settings["api_hash"]

            if self.login:
                if (phone and token) or (not phone and not token):
                    "in login mode need exactly one of phone and token"
                if phone:
                    pass

    @staticmethod
    def create_config():
        config = {"default_profile": "tdbot", "tdbot": {}}

        with open(CONFIG_DIRECTORY + "/config", "w+") as f:
            libconf.dump(config, f)
            f.close()

    def create_profile(self, config):
        config[self.profile] = {}

        with open(self.config_directory + self.config_name, "w+") as f:
            libconf.dump(config, f)
            f.close()
