"""
This script downloads all the articles on Zendesk and saves them in HTML format in a newly created folder named "Zendesk_{date}".
:author: Qrhl
"""

from ConfReader import ConfReader
import datetime
import csv
import os
import requests
import pickle
from shutil import rmtree

logs = []

config = ConfReader('zendesk_conf_test')
path_pref = "{}".format(config.get_value("BACKUP_PATH"))
zendesk = "{}".format(config.get_value("URL"))
locale = "{}".format(config.get_value("LOCALE"))


def save_restore_list(path, restore_list):
    """
    Saves a list of the articles that are backed up in a binary file (Pickle). This list will be reused to restore the articles
    :param path: str
    :param restore_list: list
    :return: /
    """
    path_res = os.path.join(path, 'Restore_List')
    with open(path_res, 'wb') as file:
        pickler = pickle.Pickler(file)
        pickler.dump(restore_list)


def load_restore_list(path):
    """
    Reads the pickle with the restore list and returns it.
    :param path: str
    :return: list
    """
    path_res = os.path.join(path, 'Restore_List')
    with open(path_res, 'rb') as file:
        pickler = pickle.Unpickler(file)
        restored = pickler.load()
        return restored


def get_dates():
    """
    Counts the folders in BackupZendesk and sorts the dates of the files
    :return: A sorted list of the dates and the number of folders
    """
    dates = []
    count_folders = 0
    for dir in os.listdir(path_pref):
        try:
            if dir.split("_")[0] == "Zendesk":
                dates.append(dir.split("_")[1])
                count_folders += 1
        except Exception:
            pass
    dates.sort()
    return dates, count_folders


def manage_dir():
    """
    Ensures that the backups are following the retention days and dispose of the old folders
    :return: path of the new folder to do the backup
    """
    days = int(config.get_value("RETENTION_DAYS"))
    date = datetime.date.today()
    backup_path = os.path.join(path_pref + "Zendesk_" + str(date))

    if not os.path.exists(path_pref):
        os.makedirs(path_pref)

    dates, count = get_dates()

    if count == days:
        rmtree(path_pref + "Zendesk_{}".format(dates[0]))
    elif count > days:
        for i in dates[:(count-days)]:
            rmtree(path_pref + "Zendesk_{}".format(i))

    if not os.path.exists(backup_path):
        os.makedirs(backup_path)
    return backup_path


def backup(backup_path):
    """
    This function connects to the Zendesk API and recovers the articles. They are then saved in a folder in backup_path.
    :param backup_path: Destination folder of the backup
    :return: None
    """
    username = "{}/token".format(config.get_value("LOGIN_USERNAME"))
    token = "{}".format(config.get_value("API_TOKEN"))
    endpoint = zendesk + '/api/v2/help_center/{locale}/articles.json'.format(locale=locale.lower())

    try:
        restore_list = load_restore_list(backup_path)
    except FileNotFoundError:
        restore_list = []

    while endpoint:
        response = requests.get(endpoint, auth=(username, token))
        if response.status_code != 200:
            e = Exception("The webpage returned a code different from 200")
            logs.append(('All', 'All', 'ERROR'))
            raise e
        data = response.json()
        for article in data['articles']:
            if article['id'] not in restore_list:
                restore_list.append(article['id'])
            title = "<h1>" + article["title"] + "</h1>"
            filename = '{id}.html'.format(id=article['id'])
            try:
                with open(os.path.join(backup_path, filename), mode='w', encoding='utf-8') as fn:
                    try:
                        fn.write(title + '\n' + article['body'])
                        logs.append((filename, article['title'], 'OK'))
                    except Exception:
                        logs.append((filename, article['title'], 'ERROR'))
            except OSError:
                logs.append((filename, article['title'], 'ERROR'))

        endpoint = data['next_page']
        save_restore_list(backup_path, restore_list)


def write_logs():
    """
    Writes the logs
    :return: None
    """
    with open(os.path.join(backup_path, '_logs.csv'), mode='wt', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(('File', 'Title', 'Status'))
        for article in logs:
            writer.writerow(article)


if __name__ == "__main__":
    try:
        backup_path = manage_dir()
        backup(backup_path)
    finally:
        write_logs()
