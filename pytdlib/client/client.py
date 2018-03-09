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

import traceback

from ctypes import CDLL
from ctypes.util import find_library
from pytdlib.log import SetLogPath, SetLogSize, SetLogLevel, SetLogErrorCallback
from pytdlib.session import Session

import time
import re
from pytdlib.api.types import (updateAuthorizationState, authorizationStateWaitTdlibParameters,
                               authorizationStateWaitEncryptionKey, authorizationStateWaitPhoneNumber,
                               authorizationStateWaitCode, authorizationStateWaitPassword, authorizationStateReady,
                               InputMessageContent, inputMessageText, ReplyMarkup, formattedText,
                               textParseModeMarkdown, textParseModeHTML, chatActionTyping)

from pytdlib.api.functions import (checkAuthenticationBotToken, setAuthenticationPhoneNumber,
                                   checkAuthenticationBotToken, checkAuthenticationCode,
                                   checkAuthenticationPassword, parseTextEntities,
                                   sendMessage, sendChatAction, forwardMessages)
import os
import libconf
import threading
from queue import Queue
from threading import Thread, Event
from signal import signal, SIGINT, SIGTERM, SIGABRT


class Client:

    def __init__(self,
                 tdjson_path: str = find_library("tdjson") or "lib/libtdjson.so",
                 profile: str = None,
                 config: str = None):
        self.tdjson = CDLL(tdjson_path)

        self.set_log_path = SetLogPath(self.tdjson)
        self.set_log_size = SetLogSize(self.tdjson)
        self.set_log_level = SetLogLevel(self.tdjson)
        self.set_log_level(0)
        self.set_log_error = SetLogErrorCallback(self.tdjson)

        self.session = Session(self.tdjson, profile=profile, config=config)

        self.send = self.session.send
        self.execute = self.session.execute

        self.update_queue = Queue()
        self.update_handler = None
        self.updates_queue = Queue()
        self.is_idle = None
        self.workers = 0
        self.login = False
        self.token_key = None
        self.phone_number = None
        self.password = None
        self.phone_code = None
        self.first_name = None
        self.last_name = None
        self.logged_in = False

    def start(self,
              login: bool = False,
              token_key: str = None,
              phone_number: str = None,
              phone_code: str or callable = None,
              password: str = None,
              first_name: str = None,
              last_name: str = None,
              workers: int = 2):

        self.login = login
        self.token_key = token_key
        self.phone_number = phone_number
        self.password = password
        self.phone_code = phone_code
        self.first_name = first_name
        self.last_name = last_name

        self.workers = workers

        self.session.start( self.updates_queue, self.workers)

        for i in range(self.workers):
            Thread(target=self.updates_worker, name="UpdatesWorker#{}".format(i + 1)).start()

        for i in range(self.workers):
            Thread(target=self.update_worker, name="UpdateWorker#{}".format(i + 1)).start()

    def stop(self):
        self.session.stop()

    def updates_worker(self):

        while True:

            update = self.updates_queue.get()

            if update is None:
                self.update_queue.put(None)
                break

            if isinstance(update, (
                    updateAuthorizationState, authorizationStateWaitTdlibParameters,
                    authorizationStateWaitEncryptionKey, authorizationStateWaitPhoneNumber,
                    authorizationStateWaitCode, authorizationStateWaitPassword,
                    authorizationStateReady)
                            ):
                self.auth(update)
            self.update_queue.put(update)

    def update_worker(self):

        while True:
            update = self.update_queue.get()

            if update is None:
                break

            if self.logged_in and self.update_handler:
                self.update_handler(update)

    def signal_handler(self, *args):
        self.stop()
        self.is_idle = False

    def idle(self, stop_signals: tuple = (SIGINT, SIGTERM, SIGABRT)):

        for s in stop_signals:
            signal(s, self.signal_handler)

        self.is_idle = True

        while self.is_idle:
            time.sleep(1)

    def set_update_handler(self, callback: callable):
        self.update_handler = callback

    def send(self, data: object, wait_response: bool = True):
        return self.session.send(data, wait_response)

    def auth(self, data):

        if isinstance(data, updateAuthorizationState):
            return self.auth(data.authorization_state)
        elif isinstance(data, authorizationStateWaitPhoneNumber):
            if self.login:
                if self.token_key is not None:
                    try:
                        return self.send(
                            checkAuthenticationBotToken(self.token_key)
                        )
                    except Exception as e:
                        self.stop()
                        print(e)

                elif self.phone_number is not None:
                    try:
                        return self.send(
                            setAuthenticationPhoneNumber(self.phone_number, False, False)
                        )
                    except Exception as e:
                        print(e)
                        self.stop()

                else:
                    login_key = input("Enter phone number or bot token-key: ")

                    while True:
                        confirm = input("Is \"{}\" correct? (y/n): ".format(login_key))

                        if confirm in ("y", "1"):
                            break
                        elif confirm in ("n", "2"):
                            login_key = input("Enter phone number or bot token-key: ")

                    is_token = re.search("(\d+):(\S+)", str(login_key))
                    try:
                        if is_token:
                            return self.send(
                                checkAuthenticationBotToken(str(login_key))
                            )
                        else:
                            self.send(
                                setAuthenticationPhoneNumber(str(login_key), False, False)
                            )
                    except Exception as e:
                        print(e)
                        self.stop()
            else:
                print("not logged in. Try running with login option")
                self.stop()

        elif isinstance(data, authorizationStateWaitCode):

            if data.is_registered:
                phone_code = input("Enter phone code: ")
                self.phone_code = "{}".format(phone_code)
            else:
                self.first_name = self.first_name if  self.first_name is not None \
                    else "{}".format(input("First name: "))
                self.last_name = self.last_name if self.last_name is not None \
                    else "{}".format(input("last name: "))

            try:
                self.send(
                    checkAuthenticationCode(self.phone_code, self.first_name, self.last_name)
                )
            except Exception as e:
                print(e)
                self.stop()

        elif isinstance(data, authorizationStateWaitPassword):
            print("Hint: {}".format(data.password_hint))
            if self.password is not None:
                if type(self.password) is not str:
                    self.password = self.password()
            else:
                self.password = "{}".format(input("Enter password: "))
                try:
                    return self.send(
                        checkAuthenticationPassword(self.password)
                    )
                except Exception as e:
                    print(e)
                    self.stop()

        elif isinstance(data, authorizationStateReady):
            self.password = None
            self.login = False
            self.logged_in = True
            return print("logged in successfully\n")


    def send_msg(self, chat_id: int , reply_to_message_id: int, disable_notification: bool, from_background: bool,
                     reply_markup: ReplyMarkup, input_message_content: InputMessageContent):
        return self.send(
            sendMessage(
                chat_id,
                reply_to_message_id,
                disable_notification,
                from_background,
                reply_markup,
                input_message_content
            )
        )

    def send_message(self, chat_id: int , text: str, reply_to_message_id:int = 0, parse_mode: str = None,
                     disable_notification: bool = False, from_background: bool = False,
                     reply_markup: ReplyMarkup = None, disable_web_page_preview: bool = False, action: bool = True):

        if action:
            self.send(sendChatAction(chat_id, chatActionTyping()), False)
            #    print(traceback.format_exc())

        if parse_mode is not None:
            parse_mode = textParseModeMarkdown() if parse_mode.lower() in ["md", "markdown"] else textParseModeHTML()
            formatted_text = self.execute(parseTextEntities(text, parse_mode))
        else:
            formatted_text = formattedText(text, [])

        return self.send_msg(
            chat_id,
            reply_to_message_id,
            disable_notification,
            from_background,
            reply_markup,
            inputMessageText(
                formattedText,
                disable_web_page_preview,
                True
            )
        )

    def forward_messages(self, chat_id: int or str, from_chat_id: int or str, message_ids: list):
        return self.send(
            forwardMessages(
                chat_id,
                from_chat_id,
                message_ids,
                False,
                False
            )
        )

