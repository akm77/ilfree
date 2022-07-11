import ipaddress
import logging
from urllib.parse import quote

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import Message, ChatActions, CallbackQuery, ForceReply
from aiogram.utils.markdown import text

from tgbot.keyboards.inline import edit_server_keyboard, myservers_callback, Action, servers_list_keyboard, \
    server_action_keyboard, confirm_keyboard, server_keys_keyboard, CALLBACK_CACHE_TIME, key_action_keyboard
from tgbot.misc.utils import size_human_read_format
from tgbot.models.outline_server import server_create, OutlineServer, server_read, server_delete, \
    server_update, server_key_sync, server_key_create, server_key_read, server_key_update, server_key_delete
from tgbot.services.outline_server_api import OutlineVPN

logger = logging.getLogger(__name__)

INVITE_MESSAGE = """Приглашаю вас подключиться к моему серверу Outline. 
С его помощью вы получите доступ к свободному Интернету, где бы вы ни находились. 
Воспользуйтесь инструкциями по приведенной в приглашении ссылке, чтобы скачать приложение Outline и создать подключение.

https://s3.amazonaws.com/outline-vpn/invite.html#{}

-----

Есть проблемы с доступом к пригласительной ссылке?

Скопируйте ключ доступа: {}
Воспользуйтесь нашими инструкциями на GitHub: https://github.com/Jigsaw-Code/outline-client/blob/master/docs/"""


class ManageServer(StatesGroup):
    enter_name = State()
    update_name = State()
    enter_ip = State()
    update_ip = State()
    enter_url = State()
    update_url = State()
    enter_key_name = State()
    update_key_name = State()


def server_info_text(server: OutlineServer) -> str:
    return text(f'Server name: {server.name}\n'
                f'IP address: {str(server.ip)}\n'
                f'Server url: {server.url}\n'
                f'State: {"✅ Active" if server.is_active else "🚫 Active"}\n')


async def new_server(message: Message, state: FSMContext):
    await ChatActions.typing()
    await state.finish()
    await message.answer('Please enter server name.',
                         reply_markup=ForceReply())
    await ManageServer.enter_name.set()


async def enter_server_name(message: Message, state: FSMContext):
    await ChatActions.typing()
    async with state.proxy() as data:
        data['server_name'] = message.text.strip()
    await message.answer(text(f"Well, server name: <b>{message.text.strip()}.</b>\n"
                              f"Please enter server IP address."),
                         reply_markup=ForceReply())
    await ManageServer.enter_ip.set()


async def update_server_name(message: Message, state: FSMContext):
    await ChatActions.typing()
    async with state.proxy() as data:
        server_name = message.text.strip()
        server_ip = data['server_ip']
        message_id = data.get('message_id')
        chat_id = data.get('chat_id')
    server = await server_update(message.bot['db_session'], primary_key_ip=ipaddress.ip_address(server_ip),
                                 name=server_name)
    markup = await edit_server_keyboard(str(server.ip), server.is_active)
    if message_id and chat_id:
        try:
            await message.answer(server_info_text(server),
                                 reply_markup=markup,
                                 disable_web_page_preview=True)
            await message.bot.delete_message(message_id=message_id,
                                             chat_id=chat_id)
        except Exception as e:
            logger.error("Error occurred while working with message.\n%r", e)
    await state.finish()


async def enter_server_ip(message: Message, state: FSMContext):
    await ChatActions.typing()
    try:
        server_ip = ipaddress.ip_address(message.text)
        async with state.proxy() as data:
            server_name = data['server_name']
            data['server_ip'] = str(server_ip)

    except ValueError:
        logger.error(f"Wrong IP address: {message.text}")
        await message.answer("Wrong IP address. \nPlease enter correct server IP address.",
                             reply_markup=ForceReply())
        await ManageServer.enter_ip.set()
        return

    await message.answer(text(f"Well, server name: <b>{server_name}.</b>\n"
                              f"IP address: <b>{str(server_ip)}</b>\n"
                              f"Please enter server manage url."),
                         reply_markup=ForceReply())
    await ManageServer.enter_url.set()


async def update_server_ip(message: Message, state: FSMContext):
    await ChatActions.typing()
    try:
        server_ip = ipaddress.ip_address(message.text)
        async with state.proxy() as data:
            primary_key_ip = data.get('server_ip', str(server_ip))
            data['server_ip'] = str(server_ip)
            message_id = data.get('message_id')
            chat_id = data.get('chat_id')
    except ValueError:
        logger.error(f"Wrong IP address: {message.text}")
        await message.answer("Wrong IP address. \nPlease enter correct server IP address.",
                             reply_markup=ForceReply())
        await ManageServer.update_ip.set()
        return

    server = await server_update(message.bot['db_session'], primary_key_ip=ipaddress.ip_address(primary_key_ip),
                                 ip=server_ip)
    markup = await edit_server_keyboard(str(server.ip), server.is_active)
    if message_id and chat_id:
        await message.answer(server_info_text(server),
                             reply_markup=markup,
                             disable_web_page_preview=True)
        await message.bot.delete_message(message_id=message_id,
                                         chat_id=chat_id)
    await state.finish()


async def enter_server_url(message: Message, state: FSMContext):
    await ChatActions.typing()
    try:
        async with state.proxy() as data:
            server_name = data['server_name']
            server_ip = ipaddress.ip_address(data['server_ip'])
            server_url = message.text

            server: OutlineServer = await server_create(message.bot['db_session'],
                                                        ip=server_ip,
                                                        url=server_url,
                                                        name=server_name)
            if not server:
                logger.error(f"Something went wrong. Could not create server object in DB.")
                await message.answer("Something went wrong.\nPlease issue /newserver command again.")
                await state.finish()
                return
    except ValueError:
        logger.error(f"Wrong server manage url: {message.text}")
        await message.answer("Wrong server manage url.\nPlease enter correct server manage url.")
        await ManageServer.enter_url.set()
        return
    except Exception as err:
        logger.error(f"Something went wrong. {err=}, {type(err)=}")
        await message.answer("Something went wrong.\nPlease issue /newserver command again.")
        await state.finish()
        return
    markup = await edit_server_keyboard(str(server.ip), server.is_active)
    await message.answer(f'New server was added.\n' + server_info_text(server),
                         reply_markup=markup,
                         disable_web_page_preview=True)
    await state.finish()


async def update_server_url(message: Message, state: FSMContext):
    await ChatActions.typing()
    try:
        async with state.proxy() as data:
            server_name = data['server_name']
            server_ip = ipaddress.ip_address(data['server_ip'])
            server_url = message.text
            message_id = data.get('message_id')
            chat_id = data.get('chat_id')

            server = await server_update(message.bot['db_session'], primary_key_ip=server_ip,
                                         url=server_url)
            markup = await edit_server_keyboard(str(server.ip), server.is_active)
            if message_id and chat_id:
                await message.answer(server_info_text(server),
                                     reply_markup=markup,
                                     disable_web_page_preview=True)
                await message.bot.delete_message(message_id=message_id,
                                                 chat_id=chat_id)
            await state.finish()
    except ValueError:
        logger.error(f"Wrong server manage url: {message.text}")
        await message.answer("Wrong server manage url.\nPlease enter correct server manage url.")
        await ManageServer.update_url.set()
    except Exception as err:
        logger.error(f"Something went wrong. {err=}, {type(err)=}")
        await message.answer("Something went wrong.\nPlease issue /myservers command again.")
        await state.finish()


async def myservers(message: Message, state: FSMContext):
    await ChatActions.typing()
    await state.finish()
    markup = await servers_list_keyboard(message.bot['db_session'])
    await message.answer(text='Choose a server from the list below:',
                         reply_markup=markup,
                         disable_web_page_preview=True)


async def myservers_call(call: CallbackQuery, callback_data: dict, state: FSMContext):
    await ChatActions.typing()
    await state.finish()
    markup = await servers_list_keyboard(call.message.bot['db_session'])
    await call.answer(cache_time=CALLBACK_CACHE_TIME)
    await call.message.edit_text(text='Choose a server from the list below:',
                                 reply_markup=markup,
                                 disable_web_page_preview=True)


async def server_actions(call: CallbackQuery, callback_data: dict):
    await ChatActions.typing()
    server = await server_read(call.message.bot['db_session'], ip=ipaddress.ip_address(callback_data['ip']))
    markup = await server_action_keyboard(str(server.ip))
    await call.answer(cache_time=CALLBACK_CACHE_TIME)

    await call.message.edit_text(f"Now server is: {server.name} ({str(server.ip)})\nWhat do you want to do?",
                                 reply_markup=markup,
                                 disable_web_page_preview=True
                                 )


async def edit_server(call: CallbackQuery, callback_data: dict):
    await ChatActions.typing()
    server = await server_read(call.message.bot['db_session'], ip=ipaddress.ip_address(callback_data['ip']))
    markup = await edit_server_keyboard(str(server.ip), server.is_active)
    await call.answer(cache_time=CALLBACK_CACHE_TIME)

    await call.message.edit_text(server_info_text(server),
                                 reply_markup=markup,
                                 disable_web_page_preview=True
                                 )


async def delete_server_confirm(call: CallbackQuery, callback_data: dict):
    await ChatActions.typing()
    server = await server_read(call.message.bot['db_session'], ip=ipaddress.ip_address(callback_data['ip']))
    markup = await confirm_keyboard(callback_data['ip'], "",
                                    Action.SERVER_DELETE,
                                    Action.SERVER_CHOOSE_ACTION)
    await call.message.edit_text("Are you sure delete the server?\n" + server_info_text(server),
                                 reply_markup=markup)


async def delete_server(call: CallbackQuery, callback_data: dict):
    await ChatActions.typing()
    await call.answer(cache_time=CALLBACK_CACHE_TIME)
    result = await server_delete(call.message.bot['db_session'], ip=ipaddress.ip_address(callback_data['ip']))
    markup = await servers_list_keyboard(call.message.bot['db_session'])
    await call.message.edit_text(text='Choose a server from the list below:',
                                 reply_markup=markup,
                                 disable_web_page_preview=True)


async def edit_server_params(call: CallbackQuery, callback_data: dict, state: FSMContext):
    await ChatActions.typing()
    server = await server_read(call.message.bot['db_session'], ip=ipaddress.ip_address(callback_data['ip']))
    await call.answer(cache_time=CALLBACK_CACHE_TIME)
    async with state.proxy() as data:
        data['server_name'] = server.name
        data['server_ip'] = str(server.ip)
        data['server_url'] = server.url
        data['message_id'] = call.message.message_id
        data['chat_id'] = call.message.chat.id
    if callback_data["action"] == Action.SERVER_EDIT_NAME:
        message = await call.message.answer(f'OK. Please send new name of server {server.name}.',
                                            reply_markup=ForceReply())
        await ManageServer.update_name.set()
    elif callback_data["action"] == Action.SERVER_EDIT_IP:
        message = await call.message.answer(f'OK. Please send new server ip for {server.name}.',
                                            reply_markup=ForceReply())
        await ManageServer.update_ip.set()
    elif callback_data["action"] == Action.SERVER_EDIT_URL:
        message = await call.message.answer(f'OK. Please send new url for {server.name}.',
                                            reply_markup=ForceReply())
        await ManageServer.update_url.set()
    elif callback_data["action"] == Action.SERVER_EDIT_STATE:
        server = await server_update(call.message.bot['db_session'],
                                     primary_key_ip=server.ip,
                                     is_active=not server.is_active)
        markup = await edit_server_keyboard(str(server.ip), server.is_active)
        await call.message.edit_text(server_info_text(server),
                                     reply_markup=markup,
                                     disable_web_page_preview=True)


async def show_keys(call: CallbackQuery, callback_data: dict, state: FSMContext):
    await ChatActions.typing()
    server = await server_read(call.message.bot['db_session'], ip=ipaddress.ip_address(callback_data['ip']))
    await call.answer(cache_time=CALLBACK_CACHE_TIME)
    server_keys = await server_key_sync(call.message.bot['db_session'],
                                        aiohttp_session=call.message.bot['http_session'],
                                        server_ip=ipaddress.ip_address(callback_data['ip']))
    markup = await server_keys_keyboard(ipaddress.ip_address(callback_data['ip']), server_keys)
    await call.message.edit_text(f"Keys on {server.name}",
                                 reply_markup=markup,
                                 disable_web_page_preview=True)


async def new_key(call: CallbackQuery, callback_data: dict, state: FSMContext):
    await ChatActions.typing()
    await call.answer(cache_time=CALLBACK_CACHE_TIME)
    await call.message.answer(text("Please enter key name."), reply_markup=ForceReply())
    await ManageServer.enter_key_name.set()
    async with state.proxy() as data:
        data['server_ip'] = callback_data['ip']
        data['message_id'] = call.message.message_id
        data['chat_id'] = call.message.chat.id


async def enter_key_name(message: Message, state: FSMContext):
    await ChatActions.typing()
    key_name = message.text.strip()
    user_id = message.from_user.id
    async with state.proxy() as data:
        server_ip = ipaddress.ip_address(data['server_ip'])
        message_id = data.get('message_id')
        chat_id = data.get('chat_id')
    try:
        server = await server_read(message.bot['db_session'], ip=server_ip)
        server_key = await server_key_create(message.bot['db_session'],
                                             message.bot['http_session'],
                                             server_ip=server_ip,
                                             key_name=key_name)
        if server_key:
            await message.bot.send_message(chat_id=user_id,
                                           text=INVITE_MESSAGE.format(quote(server_key.access_url),
                                                                      server_key.access_url))
        server_keys = await server_key_sync(message.bot['db_session'],
                                            aiohttp_session=message.bot['http_session'],
                                            server_ip=server_ip)
        markup = await server_keys_keyboard(server_ip, server_keys)
        if message_id and chat_id:
            await message.answer(f"Keys on {server.name}",
                                 reply_markup=markup,
                                 disable_web_page_preview=True)
            await message.bot.delete_message(message_id=message_id,
                                             chat_id=chat_id)
    except Exception as e:
        logger.error("Error while create new server key.\n %r", e)
    await state.finish()


async def update_key_name(message: Message, state: FSMContext):
    await ChatActions.typing()
    key_name = message.text.strip()
    async with state.proxy() as data:
        server_ip = ipaddress.ip_address(data['server_ip'])
        key_id = int(data['key_id'])
    try:
        server = await server_read(message.bot['db_session'], ip=server_ip)
        vpn = OutlineVPN(api_url=server.url, session=message.bot['http_session'], logger=logger)
        result = await vpn.rename_key(key_id=key_id, new_name=key_name)
        if result:
            server_key = await server_key_update(message.bot['db_session'],
                                                 server_ip=server_ip,
                                                 key_id=key_id,
                                                 name=key_name)
            markup = await key_action_keyboard(ip_address=server_ip, key_id=key_id)
            await message.answer(text(f"Key name: {server_key.name or 'Key id ' + str(server_key.key_id)}\n"
                                      f"Used bytes: {server_key.used_bytes:,}\n"
                                      f"What do you want to do?"),
                                 reply_markup=markup,
                                 disable_web_page_preview=True
                                 )
    except Exception as e:
        logger.error("Error while create new server key.\n %r", e)
    await state.finish()


async def key_actions(call: CallbackQuery, callback_data: dict):
    await ChatActions.typing()
    server_key = await server_key_read(call.message.bot['db_session'],
                                       server_ip=ipaddress.ip_address(callback_data['ip']),
                                       key_id=int(callback_data['key_id']))
    markup = await key_action_keyboard(ip_address=callback_data['ip'], key_id=callback_data['key_id'])
    await call.answer(cache_time=CALLBACK_CACHE_TIME)
    print(server_key.used_bytes)
    await call.message.edit_text(text(f"Key name: {server_key.name or 'Key id ' + str(server_key.key_id)}\n"
                                      f"Used bytes: {size_human_read_format(server_key.used_bytes)}\n"
                                      f"What do you want to do?"),
                                 reply_markup=markup,
                                 disable_web_page_preview=True
                                 )


async def delete_key_confirm(call: CallbackQuery, callback_data: dict):
    await ChatActions.typing()
    markup = await confirm_keyboard(callback_data['ip'], callback_data['key_id'],
                                    Action.KEY_DELETE,
                                    Action.KEY_CHOOSE_ACTION)
    server_key = await server_key_read(call.message.bot['db_session'],
                                       server_ip=ipaddress.ip_address(callback_data['ip']),
                                       key_id=int(callback_data['key_id']))
    await call.message.edit_text(text(f"Key name: {server_key.name or 'Key id ' + str(server_key.key_id)}\n"
                                      f"Used bytes: {size_human_read_format(server_key.used_bytes)}\n\n"
                                      f"Are you sure to delete this key?"),
                                 reply_markup=markup,
                                 disable_web_page_preview=True
                                 )


async def delete_key(call: CallbackQuery, callback_data: dict):
    await ChatActions.typing()
    await call.answer(cache_time=CALLBACK_CACHE_TIME)
    server = await server_read(call.message.bot['db_session'], ip=ipaddress.ip_address(callback_data['ip']))
    await server_key_delete(call.message.bot['db_session'],
                            call.message.bot['http_session'],
                            server_ip=ipaddress.ip_address(callback_data['ip']),
                            key_id=int(callback_data['key_id']))
    server_keys = await server_key_sync(call.message.bot['db_session'],
                                        aiohttp_session=call.message.bot['http_session'],
                                        server_ip=ipaddress.ip_address(callback_data['ip']))
    markup = await server_keys_keyboard(ipaddress.ip_address(callback_data['ip']), server_keys)
    await call.message.edit_text(f"Keys on {server.name}",
                                 reply_markup=markup,
                                 disable_web_page_preview=True)


async def edit_key_params(call: CallbackQuery, callback_data: dict, state: FSMContext):
    await ChatActions.typing()
    await call.answer(cache_time=CALLBACK_CACHE_TIME)
    server_ip = ipaddress.ip_address(callback_data['ip'])
    key_id = callback_data['key_id']
    async with state.proxy() as data:
        data['server_ip'] = str(server_ip)
        data['key_id'] = key_id
    server_key = await server_key_read(call.message.bot['db_session'],
                                       server_ip=server_ip,
                                       key_id=int(key_id))

    if callback_data["action"] == Action.KEY_SEND:
        if server_key:
            await call.message.bot.send_message(chat_id=call.from_user.id,
                                                text=INVITE_MESSAGE.format(quote(server_key.access_url),
                                                                           server_key.access_url),
                                                disable_web_page_preview=True)

    elif callback_data["action"] == Action.KEY_EDIT_NAME:
        message = await call.message.answer(f'OK. Please send new key name for {server_key.name}.',
                                            reply_markup=ForceReply())
        await ManageServer.update_key_name.set()


def register_manage_server(dp: Dispatcher):
    dp.register_message_handler(new_server, commands="newserver", state='*')
    dp.register_message_handler(enter_server_name, state=ManageServer.enter_name)
    dp.register_message_handler(update_server_name, state=ManageServer.update_name)
    dp.register_message_handler(enter_server_ip, state=ManageServer.enter_ip)
    dp.register_message_handler(update_server_ip, state=ManageServer.update_ip)
    dp.register_message_handler(enter_server_url, state=ManageServer.enter_url)
    dp.register_message_handler(update_server_url, state=ManageServer.update_url)
    dp.register_message_handler(myservers, commands="myservers", state='*')
    dp.register_message_handler(enter_key_name, state=ManageServer.enter_key_name)
    dp.register_message_handler(update_key_name, state=ManageServer.update_key_name)
    dp.register_callback_query_handler(myservers_call,
                                       myservers_callback.filter(action=Action.SERVER_SHOW_LIST), state='*')
    dp.register_callback_query_handler(server_actions,
                                       myservers_callback.filter(action=Action.SERVER_CHOOSE_ACTION), state='*')
    dp.register_callback_query_handler(edit_server, myservers_callback.filter(action=Action.SERVER_EDIT))
    dp.register_callback_query_handler(delete_server_confirm,
                                       myservers_callback.filter(action=Action.SERVER_CONFIRM_DELETE))
    dp.register_callback_query_handler(delete_server,
                                       myservers_callback.filter(action=Action.SERVER_DELETE))
    dp.register_callback_query_handler(edit_server_params,
                                       myservers_callback.filter(action=[Action.SERVER_EDIT_NAME,
                                                                         Action.SERVER_EDIT_IP,
                                                                         Action.SERVER_EDIT_URL,
                                                                         Action.SERVER_EDIT_STATE]))
    dp.register_callback_query_handler(show_keys, myservers_callback.filter(action=Action.SERVER_SHOW_KEYS))
    dp.register_callback_query_handler(new_key, myservers_callback.filter(action=Action.KEY_NEW))
    dp.register_callback_query_handler(key_actions,
                                       myservers_callback.filter(action=Action.KEY_CHOOSE_ACTION), state='*')
    dp.register_callback_query_handler(edit_key_params,
                                       myservers_callback.filter(action=[Action.KEY_SEND,
                                                                         Action.KEY_EDIT_NAME]))
    dp.register_callback_query_handler(delete_key_confirm,
                                       myservers_callback.filter(action=Action.KEY_CONFIRM_DELETE))
    dp.register_callback_query_handler(delete_key,
                                       myservers_callback.filter(action=Action.KEY_DELETE))
