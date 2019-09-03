import logging
from app import app


if __name__ == "__main__":
    if app.config["DEBUG"]:
        logging.basicConfig(
            format="%(asctime)s :  %(name)s : %(levelname)s : %(message)s",
            level=logging.DEBUG,
        )
        app.run(threaded=app.config["THREADED"])
    if app.config["DEVELOPMENT"]:
        raise Exception("For development, user `python app.py` instead")
