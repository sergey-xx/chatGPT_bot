"""Модуль, принимающие сообщения от пользователей в Телеграм.

И отправляющий ответ, полученный от chatGPT.
https://github.com/sergey-xx
"""

import logging
import os
import time

import openai
import requests
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

from exceptions import APIAccessError, DictError, SendMessageError

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TOKEN")
MAX_FILE_DESCR_LEN = 20
ERROR_RESPONSE = 'content_policy_violation'

openai.api_key = OPENAI_API_KEY

messages = dict()
is_image_requested = dict()


logging.basicConfig(
    level=logging.DEBUG,
    filename=os.getenv("LOGS_FILENAME"),
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
    """Функция, инициализирующая общение."""
    chat = update.effective_chat
    name = update.message.chat.first_name
    if is_image_requested.get(chat.id):
        is_image_requested.pop(chat.id)
    button = ReplyKeyboardMarkup([['/ask_picture']],
                                 resize_keyboard=True)
    hi_text = f'Теперь, задавайте свой вопрос, {format(name)}!'
    if os.getenv("DEBUG"):
        hi_text = 'Ведутся технические работы.'
    context.bot.send_message(
        chat_id=chat.id,
        text=hi_text,
        reply_markup=button)


def ask_question(update, context):
    """Функция реакции на кнопку. Возвращает к генерации текста."""
    chat = update.effective_chat
    name = update.message.chat.first_name
    if is_image_requested.get(chat.id):
        is_image_requested.pop(chat.id)
    button = ReplyKeyboardMarkup([['/ask_picture']],
                                 resize_keyboard=True)
    hi_text = f'Теперь, задавайте свой вопрос, {format(name)}!'
    if os.getenv("DEBUG"):
        hi_text = 'Ведутся технические работы.'
    context.bot.send_message(
        chat_id=chat.id,
        text=hi_text,
        reply_markup=button)


def ask_picture(update, context):
    """Функция реакции на кнопку. Позволяет генерировать картинку."""
    chat = update.effective_chat
    name = update.message.chat.first_name
    button = ReplyKeyboardMarkup([['/ask_question']],
                                 resize_keyboard=True)
    text = ('Теперь вы можете прислать запрос на картинку, '
            f'{format(name)}! Учтите, запросы платные!')
    context.bot.send_message(
        chat_id=chat.id,
        text=text,
        reply_markup=button)
    is_image_requested[chat.id] = True


def get_gpt_image(chat_id):
    """Запрашивает картинку у dall-e-3."""
    message = messages[chat_id]
    image_description = message.pop().get('content')
    try:
        logger.debug('запрашиваю картинку: "%s"', image_description)
        response = openai.Image.create(
            model="dall-e-3",
            prompt=image_description,
            size="1024x1024",
            quality="standard",
            n=1,)
    except openai.OpenAIError as error:
        logger.error(error)
        if error.code == ERROR_RESPONSE:
            return error.code

    image_url = response.data[0].url
    image = requests.get(image_url, allow_redirects=True, timeout=20).content
    time_now = int(time.monotonic())

    if len(image_description) > MAX_FILE_DESCR_LEN:
        image_description = image_description[:MAX_FILE_DESCR_LEN]

    filename = (os.getenv("IMG_FOLDER", "") +
                f'image_{image_description}_{time_now}.png')

    with open(filename, 'wb') as f:
        f.write(image)
    return image


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
    button = ReplyKeyboardMarkup([['/ask_picture']],
                                 resize_keyboard=True)

    if chat.id not in messages:
        messages[chat.id] = [{"role": "user",
                              "content": update.message.text}, ]
    else:
        messages[chat.id].append({"role": "user",
                                  "content": update.message.text})
    if is_image_requested.get(chat.id):
        image = get_gpt_image(chat.id)
        is_image_requested.pop(chat.id)
        if image == ERROR_RESPONSE:
            context.bot.send_message(chat_id=chat.id,
                                     text=('текст вашего запроса был отклонен '
                                           'сервером по этическим соображениям'
                                           ),
                                     reply_markup=button)
        try:
            context.bot.send_photo(chat.id,
                                   image,
                                   reply_markup=button)
            logger.debug('Бот отправил изображение.')
        except SendMessageError as error:
            logger.error(error)
    else:
        answer = get_gpt_answer(chat.id)
        messages[chat.id].pop()
        messages[chat.id].append({"role": "assistant", "content": answer})
        if len(messages[chat.id]) >= 5:
            messages[chat.id].pop(0)
        try:
            context.bot.send_message(chat_id=chat.id,
                                     text=answer,
                                     reply_markup=button)
            logger.debug('Бот отправил сообщение.')
        except SendMessageError as error:
            logger.error(error)


if __name__ == '__main__':
    if not check_tokens():
        exit()

    updater = Updater(token=TELEGRAM_TOKEN)
    updater.dispatcher.add_handler(CommandHandler('start',
                                                  wake_up,
                                                  run_async=True))

    updater.dispatcher.add_handler(CommandHandler('ask_picture',
                                                  ask_picture,
                                                  run_async=True))

    updater.dispatcher.add_handler(CommandHandler('ask_question',
                                                  ask_question,
                                                  run_async=True))
                                                  
    updater.dispatcher.add_handler(MessageHandler(Filters.text,
                                                  say_answer,
                                                  run_async=True))
    updater.start_polling()
    updater.idle()
