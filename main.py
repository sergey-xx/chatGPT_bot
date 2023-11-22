import os
import logging

import openai
from dotenv import load_dotenv
from telegram.ext import Updater, Filters, MessageHandler, CommandHandler
from telegram import ReplyKeyboardMarkup


from exceptions import APIAccessError, SendMessageError, DictError


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
    chat = update.effective_chat
    name = update.message.chat.first_name
    button = ReplyKeyboardMarkup([['/start']], resize_keyboard=True)
    hi_text = f'Спасибо, что вы включили меня, {format(name)}!'
    if os.getenv("DEBUG"):
        hi_text = 'Ведутся технические работы.'
    # Добавим кнопку в содержимое отправляемого сообщения
    context.bot.send_message(
        chat_id=chat.id,
        text=hi_text,
        reply_markup=button)


messages = list()


def get_gpt_answer(question):
    messages.append({"role": "user", "content": question})
    try:
        chat_completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages
            )
    except:
        raise APIAccessError('Ошибка доступа к API')
    answer = chat_completion.get(
        'choices')[0].get(
        'message').get(
        'content')
    if not answer:
        raise DictError('Пришел ответ неизвестного формата')

    print(answer)
    messages.pop()
    messages.append({"role": "assistant", "content": answer})
    if len(messages) >= 5:
        messages.pop(0)
    return answer


def say_answer(update, context):
    chat = update.effective_chat
    print(update.message.text)
    answer = get_gpt_answer(update.message.text)
    try:
        context.bot.send_message(chat_id=chat.id, text=answer)
        logger.debug('Бот отправил сообщение.')
    except SendMessageError as error:
        logger.error(error)


def main():
    if not check_tokens():
        exit()
    updater = Updater(token=TELEGRAM_TOKEN)
    updater.dispatcher.add_handler(CommandHandler('start', wake_up))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, say_answer))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
