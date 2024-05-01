import json
import os


def get_from_settings(data_name, filename='settings.json'):
    current_dir = os.path.dirname(__file__)
    settings_path = os.path.join(current_dir, filename)
    print(current_dir)
    with open(settings_path, 'r') as file:
        data = json.load(file)
    return data[data_name]
