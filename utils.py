import os
import logging
import zipfile
from pyunpack import Archive

def remove_extension(path):
    return os.path.splitext(path)[0]

def get_file_info(bot, userfile_id):
    from app import app, db
    from models import UserFiles

    with app.app_context():
        userfile = db.session.query(UserFiles).get(userfile_id)
        file_message_id = userfile.message_id
        file_id = userfile.file_id
        file = bot.getFile(file_id)
        filename = userfile.file_name
    return {
        "file_id": file_id,
        "userfile_id": userfile_id,
        "file": file,
        "message_id": file_message_id,
        "filename": filename,
        "file_extension": filename.split('.')[-1],
        "download_path": os.path.join(
            app.config['DOWLOAD_DIR'],
            '%s %s' % (userfile_id, filename)
            ),
        "extract_path": remove_extension(os.path.join(
            app.config['TMP_DIR'],
            '%s %s' % (userfile_id, filename)
            )),
    }

def extract_file(bot, chat_id, file_info):
    if file_info['file_extension'] not in ('zip', 'rar', 'txt'):
        logging.error("Incorrect file extension.")
        bot.send_message(
            chat_id=chat_id,
            text="Выбранный формат файла не поддерживается." + \
            " Пришлите, пожалуйста, файл в одном из следующих раширений: *.txt, *.zip, *.rar"
            )
        raise ValueError("Unsupported file format: %s." % file_info['file_extension'])

    file_info['file'].download(custom_path=file_info['download_path'])

    if not os.path.exists(file_info['extract_path']):
        os.makedirs(file_info['extract_path'])

    if file_info['file_extension'] == 'txt':
        file_info['file'].download(custom_path=os.path.join(file_info['extract_path'], file_info['filename']))
    elif file_info['file_extension'] in ('zip', 'rar'):
        try:
            Archive(file_info['download_path']).extractall(file_info['extract_path'])
        except Exception as e:
            logging.error(e)
            bot.send_message(
                chat_id=chat_id,
                text=[
                    "Упс! Не удалось распаковать архив \U0001F631",
                    "Проверьте, что файл в правильном формате, если так," + \
                    " то передайте следующую информацию администратору, чтобы он все исправил:",
                    "Error on unpacking file. User file: %s" % (file_info['userfile_id'], )
                    ].join("\n")
                )
            raise
    return 'OK'

def zipdir(path, out):
    zipf = zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            zipf.write(file_path, os.path.relpath(file_path, path))
    zipf.close()


