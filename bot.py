import os
import json
import logging

# THIRD PARTIES
from dotenv import load_dotenv
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler
from telegram.ext.filters import Filters

# OWN
from models import UserFiles
from utils import get_file_info, remove_extension, extract_file, zipdir
from actions import (
    transform_bwtek,
    recalibrate_bwtek,
    dep,
    process_agnp_synthesis_experiments,
)

ACTIONS_MAPPING = {
    "trans": transform_bwtek,
    "recal": recalibrate_bwtek,
    "dep": dep,
    "agnp": process_agnp_synthesis_experiments,
}

# Set globals
BASEDIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASEDIR, ".env"))
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

# Set logger
logger = logging.getLogger("IBCP-BOT")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler("ibcp-bot.log")
fh.setLevel(logging.WARNING)
formatter = logging.Formatter(
    "%(asctime)s : %(name)s : %(levelname)s : %(message)s"
)
fh.setFormatter(formatter)
logger.addHandler(fh)


# ===== COMMANDS =====
def start(bot, update):
    logger.debug("Got start command: %s" % update)
    chat_id = update.message.chat.id
    bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)
    message = [
        "Здравствуйте!\n",
        "Я бот ИБХФ РАН, который поможет автоматизировать рутинные задачи лаборатории.",
        "Я пока еще молод и не всему успел научиться.",
        "На текущий момент я умею:\n",
        " - переформатировать спетры BWTek\n",
        " - обрабатывать эксперименты ДЭФ (спросите Наташу)\n",
        " - обрабатывать эксперименты по синтезу частиц (спросите Колю)\n",
        "\nЧтобы обработать спетры просто пришлите данные в архиве *.zip или *.rar",
        "и выберете соответствующее действие. Если нужно обработать только один файл,",
        "то можно его не архифировать. Архивы *.zip более предпочтительны.",
        "\n\nЕсли возникнут сложности, обращайтесь к моему непосредственному руководителю:",
        "Гулиев Рустам, glvrst@gmail.com, +79160013525",
        "\n\nЧтобы посмотреть это сообщение еще раз просто пришлите команду /help",
    ]
    bot.send_message(chat_id=chat_id, text=" ".join(message))
    return "OK"


def unknown(bot, update):
    logger.debug("Got unknown command: %s" % update)
    chat_id = update.message.chat.id
    bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)
    bot.send_message(
        chat_id=chat_id,
        text="Я такого еще не умею. Наберите /help для просмотра инструкции и текущих возможностей.",
    )
    return "OK"


# ===== DOCUMENTS =====
def choose_document_action(bot, update):
    from app import app, db

    logger.debug("Got a message with document: %s" % update)
    chat_id = update.message.chat.id
    msg_id = update.message.message_id

    # Ignore the file if it is larger than 20Mb in size
    if update.message.document.file_size > 20 * 1024 * 1024:
        bot.send_message(
            chat_id=chat_id,
            text="Этот файл слишком большой. "
            "Из-за ограничений телеграма "
            "файлы размером больше 20Мб "
            "не удается обработать. "
            "Отправьте, пожалуйста, "
            "Ваш на файл по частям < 20Мб😊",
        )
        return "OK"

    userfile = UserFiles(
        user_id=update.message.from_user.id,
        chat_id=chat_id,
        message_id=msg_id,
        file_id=update.message.document.file_id,
        file_name=update.message.document.file_name,
    )
    logger.debug("Creating userfile...")
    with app.app_context():
        db.session.add(userfile)
        db.session.commit()
        logger.debug("Created a record for user file: %s" % userfile)
        keyboard = [
            [
                InlineKeyboardButton(
                    "Переформатировать BWTek в txt (два столбца)",
                    callback_data='{"action":"trans", "uf":"%s"}'
                    % userfile.id,
                )
            ],
            [
                InlineKeyboardButton(
                    "Рекалибровать BWTek",
                    callback_data='{"action":"recal", "uf":"%s"}'
                    % userfile.id,
                )
            ],
            [
                InlineKeyboardButton(
                    "Посчитать для ДЭФ",
                    callback_data='{"action":"dep", "uf":"%s"}' % userfile.id,
                )
            ],
            [
                InlineKeyboardButton(
                    "Обработать результаты по синтезу частиц",
                    callback_data='{"action":"agnp", "uf":"%s"}' % userfile.id,
                )
            ],
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    bot.send_message(
        chat_id=chat_id, text="Что мне сделать?", reply_markup=reply_markup
    )

    return "OK"


# ===== INLINE BUTTONS =====
def inline_buttons_handler(bot, update):
    from app import app, db

    query = update.callback_query
    chat_id = query.message.chat_id

    logger.debug("Got an inline button action: %s" % query.data)
    bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)
    # Try to get params
    try:
        params = json.loads(query.data)
        action = params.get("action")
        userfile_id = int(params.get("uf"))
    except Exception as e:
        logger.error(e)
        bot.send_message(
            chat_id=chat_id,
            text="\n".join(
                [
                    "Упс! Что-то пошло не так 😱",
                    "Передайте это администратору, чтобы он все исправил:",
                    "Query data: %s" % query.data,
                    "Exception: %s" % e,
                ]
            ),
        )
        raise

    # Try to get info about file from db
    file_info = get_file_info(bot, userfile_id)
    if action in ACTIONS_MAPPING:
        outfile = os.path.join(
            app.config["PROCESSED_DIR"],
            "%s %s %s.zip"
            % (
                remove_extension(file_info["filename"]),
                file_info["userfile_id"],
                action,
            ),
        )
        bot.send_message(text="Сейчас посмотрю...⏳", chat_id=chat_id)
        try:
            extract_file(bot, chat_id, file_info)
            statuses = ACTIONS_MAPPING[action](file_info["extract_path"])

            if any(statuses.values()):
                zipdir(file_info["extract_path"], outfile)
                bot.send_message(chat_id=chat_id, text="Готово!🚀")
                bot.send_document(
                    chat_id=chat_id,
                    document=open(outfile, "rb"),
                    filename=os.path.basename(outfile),
                    reply_to_message_id=file_info["message_id"],
                )
                if not all(statuses.values()):
                    message = "⚠️ Следующие файлы не удалось обработать: ⚠️\n"
                    for file, status in statuses.items():
                        if not status:
                            file_path = os.path.relpath(
                                file, file_info["extract_path"]
                            )
                            # Telegram has limit for message length, so we
                            # split the message in case it is too long (> 4096)
                            if len(message) + len(file_path) + 10 < 4096:
                                message += f"\n ❌ {file_path}"
                            else:
                                bot.send_message(chat_id=chat_id, text=message)
                                message = f" ❌ {file_path}"
                    bot.send_message(chat_id=chat_id, text=message)
            else:
                bot.send_message(
                    chat_id=chat_id,
                    text="Не удалось обработать данные. Проверьте, что файлы предоставлены в нужном формате.",
                )
        except Exception as e:
            logger.error(e)
            bot.send_message(
                chat_id=chat_id,
                text="\n".join(
                    [
                        "Упс! Что-то пошло не так 😱",
                        "Передайте это администратору, чтобы он все исправил:",
                        "Query data: %s" % query.data,
                        "Exception: %s" % e,
                    ]
                ),
            )
            raise
    else:
        bot.send_message(
            chat_id=chat_id,
            text="Данная команда в процессе реализации и пока не доступна 😞",
        )
    return "OK"


# ===== SET HANDLERS =====
bot = telegram.Bot(TOKEN)
updater = telegram.ext.Updater(bot=bot)
updater.dispatcher.add_handler(CommandHandler("help", start))
updater.dispatcher.add_handler(CommandHandler("start", start))
updater.dispatcher.add_handler(
    MessageHandler(Filters.document, callback=choose_document_action)
)
updater.dispatcher.add_handler(
    CallbackQueryHandler(callback=inline_buttons_handler)
)
updater.dispatcher.add_handler(MessageHandler(Filters.all, unknown))
dispatcher = updater.dispatcher
