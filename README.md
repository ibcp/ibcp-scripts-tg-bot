# IBCP telegram bot for automation

This is a telegram bot to automate routine tasks of my collegues from Emanuel Institute of Biochemical Physics (IBCP RAS).

The bot is written using `python-telegram-bot` and `Flask` python webframework. It is structured for better developing experience and can be used as a template:
- .env file
- different Developmend and Production confs
- **webhooks on Production, polling on Dev!**

# Deploy and development
1. `git clone https://github.com/rguliev/ibcp-scripts-tg-bot.git`
1. `cd ibcp-scripts-tg-bot`
1. `mkdir tmp downloads processed_files` - add required folders
1. `pipenv install` - install required packages
1. `cp .env.example .env` + `vim .env` - set your env
1. `python manage.py db migrate` + `python manage.py db upgrade` - migrate database
1. DEV: `python app.py` - this will start bot in polling mode
1. PROD: Open `https://host/setwebhook` in browser and make sure that webhook works
