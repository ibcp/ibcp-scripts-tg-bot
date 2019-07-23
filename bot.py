import os
import json
import zipfile
import logging
# THIRD PARTIES
from dotenv import load_dotenv
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler
from telegram.ext.filters import Filters
# OWN
from models import UserFiles
from utils import *
from actions import *

ACTIONS_MAPPING = {
    'recal': recal,
}

# Set globals
BASEDIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASEDIR, '.env'))
TOKEN = os.environ['TELEGRAM_BOT_TOKEN']

# Set logger
logger = logging.getLogger('IBCP-BOT')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('ibcp-bot.log')
fh.setLevel(logging.WARNING)
formatter = logging.Formatter('%(asctime)s : %(name)s : %(levelname)s : %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

def hello(bot, update):
    logger.debug("Got hello command: %s" % update)
    chat_id = update.message.chat.id
    bot.send_chat_action(chat_id=chat_id,action=telegram.ChatAction.TYPING)
    bot.send_message(chat_id=chat_id, text='Hi there! 👋')
    return 'OK'

def reply_upper(bot, update):
    logger.debug("Got a text message: %s" % update)
    chat_id = update.message.chat.id
    msg_id = update.message.message_id
    # Telegram understands UTF-8, so encode text for unicode compatibility
    text = update.message.text.encode('utf-8').decode()
    bot.send_chat_action(chat_id=chat_id,action=telegram.ChatAction.TYPING)
    bot.send_message(chat_id=chat_id, text=text.upper(), reply_to_message_id=msg_id)
    return 'OK'

def choose_document_action(bot, update):
    from app import app, db
    logger.debug("Got a message with document: %s" % update)
    chat_id = update.message.chat.id
    msg_id = update.message.message_id

    userfile = UserFiles(
        user_id = update.message.from_user.id,
        chat_id = chat_id,
        message_id = msg_id,
        file_id = update.message.document.file_id,
        file_name = update.message.document.file_name,
        )
    logger.debug("Creating userfile...")
    with app.app_context():
        db.session.add(userfile)
        db.session.commit()
        logger.debug('Created a record for user file: %s' % userfile)
        keyboard = [
            [InlineKeyboardButton("Рекалибровать BWTek", callback_data='{"action":"recal", "uf":"%s"}' % userfile.id)],
            [InlineKeyboardButton("Посчитать для ДЭФ", callback_data='{"action":"dep", "uf":"%s"}' % userfile.id)]
            ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    bot.send_message(chat_id=chat_id, text='Что мне сделать?', reply_markup=reply_markup)

    return 'OK'

def inline_buttons_handler(bot, update):
    from app import app, db
    query = update.callback_query
    chat_id = query.message.chat_id

    logger.debug('Got an inline button action: %s' % query.data)
    bot.send_chat_action(chat_id=chat_id,action=telegram.ChatAction.TYPING)
    # Try to get params
    try:
        params = json.loads(query.data)
        action = params.get('action')
        userfile_id = int(params.get('uf'))
    except Exception as e:
        logger.error(e)
        bot.send_message(
            chat_id=chat_id,
            text=[
                "Упс! Что-то пошло не так 😱",
                "Передайте это администратору, чтобы он все исправил:",
                "Query data: %s" % query.data,
                "Exception: %s" % e,
                ].join("\n")
            )
        raise

    # Try to get info about file from db
    file_info = get_file_info(bot, userfile_id)
    if action in ACTIONS_MAPPING:
        outfile = os.path.join(
            app.config['PROCESSED_DIR'],
            '%s %s %s.zip' % (remove_extension(file_info['filename']), file_info['userfile_id'], action)
            )
        bot.send_message(text="Сейчас посмотрю...⏳", chat_id=chat_id)
        try:
            extract_file(bot, chat_id, file_info)
            statuses = ACTIONS_MAPPING[action](file_info['extract_path'])
            if any(statuses.values()):
                zipdir(file_info['extract_path'], outfile)
                bot.send_message(chat_id=chat_id, text='Готово! 🚀')
                bot.send_document(
                    chat_id=chat_id,
                    document=open(outfile, 'rb'),
                    filename=os.path.basename(outfile),
                    reply_to_message_id=file_info['message_id']
                    )
                if not all(statuses.values()):
                    message = "⚠️ Следующие файлы не удалось обработать: ⚠️\n"
                    for file, status in statuses.items():
                        if not status:
                            message += "\n ❌ %s" % os.path.relpath(file, file_info['extract_path'])
                    bot.send_message(chat_id=chat_id, text=message)
            else:
                bot.send_message(chat_id=chat_id, text='Не удалось обработать данные. Проверьте, что файлы предоставлены в нужном формате.')
        except Exception as e:
            logger.error(e)
            bot.send_message(
                chat_id=chat_id,
                text=[
                    "Упс! Что-то пошло не так 😱",
                    "Передайте это администратору, чтобы он все исправил:",
                    "Query data: %s" % query.data,
                    "Exception: %s" % e,
                    ].join("\n")
                )
            raise
    else:
        bot.send_message(
            chat_id=chat_id,
            text='Данная команда в процессе реализации и пока не доступна 😞'
        )
    return 'OK'

bot = telegram.Bot(TOKEN)
updater = telegram.ext.Updater(bot=bot)
updater.dispatcher.add_handler(CommandHandler('hello', hello))
updater.dispatcher.add_handler(MessageHandler(Filters.text, callback=reply_upper))
updater.dispatcher.add_handler(MessageHandler(Filters.document, callback=choose_document_action))
updater.dispatcher.add_handler(CallbackQueryHandler(callback=inline_buttons_handler))
dispatcher = updater.dispatcher
