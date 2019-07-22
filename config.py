import os
from dotenv import load_dotenv
BASEDIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASEDIR, '.env'))


class Config(object):
    DEBUG = False
    DEVELOPMENT = False
    CSRF_ENABLED = True
    THREADED = False
    SECRET_KEY = os.environ['SECRET_KEY']
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']


class ProductionConfig(Config):
    DEBUG = False
    THREADED = True

class DevelopmentConfig(Config):
    DEVELOPMENT = True
    DEBUG = True
