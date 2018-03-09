# demo-pytdlib
<p4>pyTDLib - python bindings for TDLib (Telegram Database Library) JSON API: https://github.com/tdlib/td

## Installation
You first need to install

+ [tdlib](https://github.com/tdlib/td)

then
```
python3 setup.py
```

### Example:
```py
from pytdlib import Client
from pytdlib.api.types import updateNewMessage, messageText

bot = Client()

bot.start(login=True)

def updt_hndlr(update):
    if isinstance(update, updateNewMessage):
        msg = update.message
        if isinstance(msg.content, messageText):
            text = msg.content.text.text

            if text == "ping":
                bot.send_message(msg.chat_id, "*PING*", reply_to_message_id=msg.id, parse_mode="md", action=True)

bot.set_update_handler(updt_hndlr)
bot.idle()
```
