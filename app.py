# BUILD-IN
import os
import logging
# THIRD PARTIES
from dotenv import load_dotenv
from flask import Flask, request
import telegram
# OWN
from models import db

# Load .env variables
BASEDIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASEDIR, '.env'))
HOST = os.environ['HOST']

# Create an app
app = Flask(__name__)
app.config.from_object(os.environ['FLASK_APP_SETTINGS'])
db.init_app(app)
from bot import bot, updater, dispatcher

@app.route('/')
def hello_world():
    return 'Hello Flask!'

@app.route('/webhook/'+app.config['BOT_TOKEN'], methods=['POST'])
def webhook():
    # Retrieve the message in JSON and then transform it to Telegram object
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"

@app.route('/setwebhook', methods=['GET', 'POST'])
def set_webhook():
    # Set the webhook for the bot
    s = bot.setWebhook('https://{HOST}/webhook/{TOKEN}'.format(HOST=HOST, TOKEN=app.config['BOT_TOKEN']))
    if s:
        return "Webhook setup is OK"
    else:
        raise Exception("Webhook setup failed")

if __name__ == '__main__':
    if app.config['DEBUG']:
        logging.basicConfig(
            format='%(asctime)s :  %(name)s : %(levelname)s : %(message)s',
            level=logging.DEBUG
            )

    if app.config['DEVELOPMENT']:
        updater.start_polling()
        updater.idle()
    app.run(threaded=app.config['THREADED'])

