from app import app
from bot import dispatcher

if __name__ == '__main__':
    if app.config['DEBUG']:
        updater.start_polling()
    else:
        bot.setWebhook('https://{HOST}/webhook/{TOKEN}'.format(HOST=HOST, TOKEN=TOKEN))
    app.run(debug=DEBUG, threaded=True)
    
