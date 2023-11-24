"""Модуль, принимающие сообщения от пользователей в Телеграм.

И отправляющий ответ, полученный от chatGPT.
https://github.com/sergey-xx
"""

import logging
import os

import openai
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

from exceptions import APIAccessError, DictError, SendMessageError

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TOKEN")

openai.api_key = OPENAI_API_KEY

logging.basicConfig(
    level=logging.DEBUG,
    filename='/logs/program.log',
    format='%(asctime)s, %(levelname)s, %(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def check_tokens():
    """Проверяет наличие необходимых токенов."""
    if not OPENAI_API_KEY:
        logger.critical('Не обнаружен токен API OpenAI')
        return False
    if not TELEGRAM_TOKEN:
        logger.critical('Не обнаружен токен Телеграмма')
        return False
    return True


def wake_up(update, context):
    """Функция реакции на кнопку. Пока не имеет особого смысла."""
    chat = update.effective_chat
    name = update.message.chat.first_name
    button = ReplyKeyboardMarkup([['/start']], resize_keyboard=True)
    hi_text = f'Спасибо, что вы включили меня, {format(name)}!'
    if os.getenv("DEBUG"):
        hi_text = 'Ведутся технические работы.'
    context.bot.send_message(
        chat_id=chat.id,
        text=hi_text,
        reply_markup=button)


# тут хранится история. Для каждого чата история своя.
messages = dict()


def get_gpt_answer(chat_id):
    """Функция, запрашивающая ответ у ChatGPT."""
    message = messages[chat_id]
    try:
        chat_completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=message
            )
    except APIAccessError as error:
        logger.error(error)

    answer = chat_completion.get(
        'choices')[0].get(
        'message').get(
        'content')
    if not answer:
        raise DictError('Пришел ответ неизвестного формата')

    return answer


def say_answer(update, context):
    """Основная функция, следящая за новыми сообщениями и посылающая ответ."""
    chat = update.effective_chat
    if chat.id not in messages:
        messages[chat.id] = [{"role": "user",
                              "content": update.message.text}, ]
    else:
        messages[chat.id].append({"role": "user",
                                  "content": update.message.text})
    answer = get_gpt_answer(chat.id)
    messages[chat.id].pop()
    messages[chat.id].append({"role": "assistant", "content": answer})
    if len(messages[chat.id]) >= 5:
        messages[chat.id].pop(0)

    try:
        context.bot.send_message(chat_id=chat.id, text=answer)
        logger.debug('Бот отправил сообщение.')
    except SendMessageError as error:
        logger.error(error)


def main():
    """Функция main."""
    if not check_tokens():
        exit()
    updater = Updater(token=TELEGRAM_TOKEN)
    updater.dispatcher.add_handler(CommandHandler('start', wake_up))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, say_answer))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
