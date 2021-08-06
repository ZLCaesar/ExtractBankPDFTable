import json
from configparser import ConfigParser

def get_config(bank):
    with open('package/config/bankmap.json') as f:
        bankmap = json.load(f)
    bank = bankmap.get(bank)
    config_dict = {}
    config = ConfigParser()
    config.read('package/config/config.ini')
    start_from_this = config.get(bank, 'start_from_this')
    under_this = config.get(bank, 'under_this')
    above_this = config.get(bank, 'above_this')
    use_fitz = config.getboolean(bank, 'use_fitz')
    no_vertical_page = config.getint(bank, 'no_vertical_page')
    config_dict['no_vertical_page'] = no_vertical_page
    config_dict['start_from_this'] = start_from_this.split(', ')
    config_dict['under_this'] = under_this.split(', ')
    config_dict['above_this'] = above_this.split(', ')
    config_dict['use_fitz'] = use_fitz
    config_dict['bank_name'] = bank

    return config_dict