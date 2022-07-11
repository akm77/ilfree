from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import Message, ChatActions, ReplyKeyboardRemove


async def user_start(message: Message, state: FSMContext):
    await ChatActions.typing()
    await state.finish()
    await message.reply("Hello, user!", reply_markup=ReplyKeyboardRemove())


def register_user(dp: Dispatcher):
    dp.register_message_handler(user_start, commands=["start"], state="*")
