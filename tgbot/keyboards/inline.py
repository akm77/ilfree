from dataclasses import dataclass
from typing import List

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData
from sqlalchemy.orm import sessionmaker

from tgbot.models.outline_server import servers_list, ServerKey


# Callback actions
@dataclass(frozen=True)
class Action:
    SERVER_SHOW_LIST: str = '01'
    SERVER_CHOOSE_ACTION: str = '06'
    SERVER_EDIT: str = '11'
    SERVER_CONFIRM_DELETE: str = '16'
    SERVER_DELETE: str = '21'
    SERVER_SHOW_KEYS: str = '26'
    SERVER_EDIT_NAME: str = '31'
    SERVER_EDIT_IP: str = '36'
    SERVER_EDIT_URL: str = '41'
    SERVER_EDIT_STATE: str = '46'
    KEY_CHOOSE_ACTION: str = '51'
    KEY_NEW: str = '56'
    KEY_SEND: str = '61'
    KEY_EDIT_NAME: str = '66'
    KEY_CONFIRM_DELETE: str = '71'
    KEY_DELETE: str = '76'


myservers_callback = CallbackData("server", "action", "ip", "key_id")
CALLBACK_CACHE_TIME = 3


async def confirm_keyboard(ip_address: str, key_id: str, yes_action: str, no_action: str) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(text='Yes',
                                    callback_data=myservers_callback.new(action=yes_action,
                                                                         ip=ip_address,
                                                                         key_id=key_id)),
               InlineKeyboardButton(text='No',
                                    callback_data=myservers_callback.new(action=no_action,
                                                                         ip=ip_address,
                                                                         key_id=key_id))
               )
    return markup


async def servers_list_keyboard(Session: sessionmaker) -> InlineKeyboardMarkup:
    servers = await servers_list(Session)
    row_buttons = (InlineKeyboardButton(text="✅ " + server.name if server.is_active else "🚫 " + server.name,
                                        callback_data=myservers_callback.new(action=Action.SERVER_CHOOSE_ACTION,
                                                                             ip=server.ip,
                                                                             key_id="")) for server in servers)
    markup = InlineKeyboardMarkup(row_width=2)
    _ = list(markup.insert(button) for button in row_buttons)
    return markup


async def server_action_keyboard(ip_address: str) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(text='📝 Edit',
                                    callback_data=myservers_callback.new(action=Action.SERVER_EDIT,
                                                                         ip=ip_address,
                                                                         key_id="")),
               InlineKeyboardButton(text='🗑 Delete',
                                    callback_data=myservers_callback.new(action=Action.SERVER_CONFIRM_DELETE,
                                                                         ip=ip_address,
                                                                         key_id="")),
               InlineKeyboardButton(text='🔑 Keys',
                                    callback_data=myservers_callback.new(action=Action.SERVER_SHOW_KEYS,
                                                                         ip=ip_address,
                                                                         key_id=""))
               )

    markup.add(InlineKeyboardButton(text='<< Back to servers list',
                                    callback_data=myservers_callback.new(action=Action.SERVER_SHOW_LIST,
                                                                         ip=ip_address,
                                                                         key_id="")))

    return markup


async def edit_server_keyboard(ip_address: str, is_active: bool = True) -> InlineKeyboardMarkup:
    state = "✅ Active" if is_active else "🚫 Active"
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(text='📝 Name',
                                    callback_data=myservers_callback.new(action=Action.SERVER_EDIT_NAME,
                                                                         ip=ip_address,
                                                                         key_id="")),
               InlineKeyboardButton(text='📝 IP',
                                    callback_data=myservers_callback.new(action=Action.SERVER_EDIT_IP,
                                                                         ip=ip_address,
                                                                         key_id="")),
               InlineKeyboardButton(text='📝 url',
                                    callback_data=myservers_callback.new(action=Action.SERVER_EDIT_URL,
                                                                         ip=ip_address,
                                                                         key_id="")),
               InlineKeyboardButton(text=state,
                                    callback_data=myservers_callback.new(action=Action.SERVER_EDIT_STATE,
                                                                         ip=ip_address,
                                                                         key_id=""))
               )
    markup.add(InlineKeyboardButton(text='<< Back to server',
                                    callback_data=myservers_callback.new(action=Action.SERVER_CHOOSE_ACTION,
                                                                         ip=ip_address,
                                                                         key_id="")))
    return markup


async def server_keys_keyboard(ip_address: str, server_keys: List[ServerKey]) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    row_buttons = (InlineKeyboardButton(text=key.name if len(key.name) else "<...>",
                                        callback_data=myservers_callback.new(action=Action.KEY_CHOOSE_ACTION,
                                                                             ip=ip_address,
                                                                             key_id=key.key_id)) for key in server_keys)
    markup = InlineKeyboardMarkup(row_width=2)
    _ = list(markup.insert(button) for button in row_buttons)
    markup.add(InlineKeyboardButton(text='🔑 New key',
                                    callback_data=myservers_callback.new(action=Action.KEY_NEW,
                                                                         ip=ip_address,
                                                                         key_id="")))
    markup.add(InlineKeyboardButton(text='<< Back to server',
                                    callback_data=myservers_callback.new(action=Action.SERVER_CHOOSE_ACTION,
                                                                         ip=ip_address,
                                                                         key_id="")))
    return markup


async def key_action_keyboard(ip_address: str, key_id: int) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(text='🔑 Send key',
                                    callback_data=myservers_callback.new(action=Action.KEY_SEND,
                                                                         ip=ip_address,
                                                                         key_id=key_id)),
               InlineKeyboardButton(text='📝 Rename',
                                    callback_data=myservers_callback.new(action=Action.KEY_EDIT_NAME,
                                                                         ip=ip_address,
                                                                         key_id=key_id)),
               InlineKeyboardButton(text='🗑 Delete',
                                    callback_data=myservers_callback.new(action=Action.KEY_CONFIRM_DELETE,
                                                                         ip=ip_address,
                                                                         key_id=key_id))
               )

    markup.add(InlineKeyboardButton(text='<< Back to keys',
                                    callback_data=myservers_callback.new(action=Action.SERVER_SHOW_KEYS,
                                                                         ip=ip_address,
                                                                         key_id="")))

    return markup
