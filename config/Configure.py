import json
from configparser import ConfigParser

def get_config(bank):
    with open('package/config/bankmap.json', encoding='utf-8') as f:
        bankmap = json.load(f)
    bank = bankmap.get(bank)
    config_dict = {}
    config = ConfigParser()
    config.read('package/config/config.ini', encoding='utf-8')
    config_dict['bank_name'] = bank
    for item in config.items(bank):
        try:
            config_dict[item[0]] = config.getint(bank, item[0])
        except:
            try:
                config_dict[item[0]] = config.getfloat(bank, item[0])
            except:
                try:
                    config_dict[item[0]] = config.getboolean(bank, item[0])
                except:
                    config_dict[item[0]] = config.get(bank, item[0]).split(', ')
                    if config_dict[item[0]] == ['[]']:
                        config_dict[item[0]] = []

    return config_dict