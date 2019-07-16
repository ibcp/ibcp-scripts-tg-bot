import os
import logging
# THIRD PARTIES
from dotenv import load_dotenv
import telegram
from telegram.ext import CommandHandler, MessageHandler

# Set globals
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
TOKEN = os.environ['TOKEN']
HOST = os.environ['HOST']
PORT = os.environ['PORT']
DEBUG = bool(int(os.environ['DEBUG']))

bot = telegram.Bot(TOKEN)
dispatcher = telegram.ext.Dispatcher(bot, None)

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

    bot.sendMessage(chat_id=chat_id, text=text.lower(), reply_to_message_id=msg_id)

    return 'OK'

dispatcher.add_handler(CommandHandler('hello', hello))
dispatcher.add_handler(MessageHandler(None, callback=reply))

if __name__ == '__main__':
    updater = telegram.ext.Updater(bot=bot)
    updater.dispatcher = dispatcher
    if DEBUG:
        updater.start_polling()
    else:
        updater.start_webhook(listen=HOST, port=PORT, url_path='webhook')
    updater.idle()
