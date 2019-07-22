from app import app
from bot import dispatcher


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
