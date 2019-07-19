# BUILD-IN
import os
import sqlite3
import logging
from logging.handlers import RotatingFileHandler
# THIRD PARTIES
from dotenv import load_dotenv
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
import telegram
from telegram.ext import Updater
# OWN
from bot import bot, updater, dispatcher
# Load env variables
BASEDIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASEDIR, '.env'))

app = Flask(__name__)
app.config.from_object(os.environ['FLASK_APP_SETTINGS'])
db = SQLAlchemy(app)

from models import *

# Set globals
DEBUG = app.config['DEBUG']
TOKEN = app.config['BOT_TOKEN']
HOST = os.environ['HOST']

# Set logging for debugging
if DEBUG:
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

@app.route('/')
def hello_world():
    return 'Hello Flask!'

@app.route('/webhook/'+TOKEN, methods=['POST'])
def webhook():
    # Retrieve the message in JSON and then transform it to Telegram object
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
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
        updater.start_polling()
    else:
        bot.setWebhook('https://{HOST}/webhook/{TOKEN}'.format(HOST=HOST, TOKEN=TOKEN))
    app.run(debug=DEBUG, threaded=True)

