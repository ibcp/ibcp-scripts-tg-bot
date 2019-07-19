import os
import logging
# THIRD PARTIES
from dotenv import load_dotenv
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler
from telegram.ext.filters import Filters

# Set globals
BASEDIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASEDIR, '.env'))
TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
HOST = os.environ['HOST']
PORT = os.environ['PORT']

bot = telegram.Bot(TOKEN)
#dispatcher = telegram.ext.Dispatcher(bot, None)

def hello(bot, update):
    logging.debug("Got hello command!")
    chat_id = update.message.chat.id
    bot.send_message(chat_id=chat_id, text='Hi there!')
    return 'Hello World!'

def reply_upper(bot, update):
    chat_id = update.message.chat.id
    msg_id = update.message.message_id

    # Telegram understands UTF-8, so encode text for unicode compatibility
    text = update.message.text.encode('utf-8').decode()
    logging.debug("Got text message :", text)

    bot.send_message(chat_id=chat_id, text=text.upper(), reply_to_message_id=msg_id)

    return 'OK'

def choose_document_action(bot, update):
    chat_id = update.message.chat.id
    msg_id = update.message.message_id

    keyboard = [
        [InlineKeyboardButton("Рекалибровать BWTek", callback_data='recal:%s:recal' % update.message.document.file_id)],
        [InlineKeyboardButton("Посчитать для ДЭФ", callback_data='document:%s:dep' % update.message.document.file_id)]
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    bot.send_message(chat_id=chat_id, text='Что мне сделать?', reply_markup=reply_markup)

    return 'OK'

def inline_buttons_handler(bot, update):
    query = update.callback_query
    chat_id = query.message.chat_id

    bot.send_chat_action(chat_id=chat_id,action=telegram.ChatAction.TYPING)
    file = bot.getFile(query.data.split(':')[1])
    file_path = 'downloads/%s %s' % (file.file_id, os.path.basename(file.file_path))
    file.download(custom_path=file_path)
    bot.edit_message_text(text="Готово! Скоро пришлю обработанные файлы",chat_id=chat_id, message_id=query.message.message_id, document=open(file_path, 'rb'))
    bot.send_document(chat_id=chat_id, document=open(file_path, 'rb'), filename=os.path.basename(file.file_path), reply_to_message_id=query.message.message_id)
    return 'OK'

updater = telegram.ext.Updater(bot=bot)
updater.dispatcher.add_handler(CommandHandler('hello', hello))
updater.dispatcher.add_handler(MessageHandler(Filters.text, callback=reply_upper))
updater.dispatcher.add_handler(MessageHandler(Filters.document, callback=choose_document_action))
updater.dispatcher.add_handler(CallbackQueryHandler(callback=inline_buttons_handler))
dispatcher = updater.dispatcher
