from app import app

if __name__ == '__main__':
    if DEBUG:
        updater = Updater(bot=bot)
        updater.dispatcher = dp
        updater.start_polling()
        updater.idle()
    else:
        app.run(debug=True, threaded=True)
