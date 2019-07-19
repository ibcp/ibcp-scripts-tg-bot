import os
from dotenv import load_dotenv
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

from app import app, db

load_dotenv('.env')

app.config.from_object(os.environ['FLASK_APP_SETTINGS'])

migrate = Migrate(app, db)
manager = Manager(app)

manager.add_command('db', MigrateCommand)


if __name__ == '__main__':
    manager.run()