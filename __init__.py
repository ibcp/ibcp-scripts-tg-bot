# BUILD-IN
import os
import logging
from logging.handlers import RotatingFileHandler

# THIRD PARTIES
from flask import Flask, request
from dotenv import load_dotenv
import telegram
from telegram.ext import Updater

# OWN
from bot import bot, dispatcher as dp

# Set globals
load_dotenv('.env')
TOKEN = os.environ['TOKEN']
HOST = os.environ['HOST']
DEBUG = bool(int(os.environ['DEBUG']))

# Set logging for debugging
if DEBUG:
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = Flask(__name__)

@app.route('/')
def hello_world():
    app.logger.debug("Entered home page")
    return 'Hello Flask!'

@app.route('/webhook/'+TOKEN, methods=['POST'])
def webhook():
    # retrieve the message in JSON and then transform it to Telegram object
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    dp.process_update(update)
    return "OK"

@app.route('/setwebhook', methods=['GET', 'POST'])
def set_webhook():
    # Set the webhook for the bot
    s = bot.setWebhook('https://{HOST}/webhook/{TOKEN}'.format(HOST=HOST, TOKEN=TOKEN))
    if s:
        return "webhook setup ok"
    else:
        raise Exception("webhook setup failed")

if __name__ == '__main__':
    if DEBUG:
        updater = Updater(bot=bot)
        updater.dispatcher = dp
        updater.start_polling()
        updater.idle()
    else:
        app.run(debug=True, threaded=True)

