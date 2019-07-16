import os
import logging
# THIRD PARTIES
from dotenv import load_dotenv
from flask import Flask, request
import telegram
from telegram.ext import Updater, InlineQueryHandler, CommandHandler, MessageHandler

# Set globals
load_dotenv('.env')
TOKEN = os.environ['TOKEN']
HOST = os.environ['HOST']
PORT = os.environ['PORT']
DEBUG = bool(int(os.environ['DEBUG']))

# Set logging for debugging
if DEBUG:
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

bot = telegram.Bot(TOKEN)
app = Flask(__name__)

def hello(bot, update):
    logging.debug("Got hello command!")
    chat_id = update.message.chat.id
    bot.sendMessage(chat_id=chat_id, text='Hi there!')
    return 'Hello World!'

def reply(bot, update):
    chat_id = update.message.chat.id
    msg_id = update.message.message_id

    # Telegram understands UTF-8, so encode text for unicode compatibility
    text = update.message.text.encode('utf-8').decode()
    logging.debug("Got text message :", text)

    bot.sendMessage(chat_id=chat_id, text=text.upper(), reply_to_message_id=msg_id)

    return 'OK'

if __name__ == '__main__':
    updater = Updater(bot=bot)
    updater.dispatcher.add_handler(CommandHandler('hello', hello))
    updater.dispatcher.add_handler(MessageHandler(None, callback=reply))

    if DEBUG:
        updater.start_polling()
    else:
        updater.start_webhook()

    updater.idle()
    app.run(debug=DEBUG, threaded=True)