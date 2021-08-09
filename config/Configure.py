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
    config_dict['no_vertical_page'] = config.getint(bank, 'no_vertical_page')
    config_dict['start_from_this'] = config.get(bank, 'start_from_this').split(', ')
    config_dict['under_this'] = config.get(bank, 'under_this').split(', ')
    config_dict['above_this'] = config.get(bank, 'above_this').split(', ')
    config_dict['use_fitz'] = config.getboolean(bank, 'use_fitz')
    config_dict['bound_flag_dis_tolerance'] = config.getint(bank, 'bound_flag_dis_tolerance')
    config_dict['up_deviation_tolerance'] = config.getint(bank, 'up_deviation_tolerance')
    config_dict['down_deviation_tolerance'] = config.getint(bank, 'down_deviation_tolerance')
    config_dict['curves_min_margin'] = config.getint(bank, 'curves_min_margin')
    config_dict['max_adjacent_dis'] = config.getint(bank, 'max_adjacent_dis')
    config_dict['multi_cell_tolerance_rate'] = config.getfloat(bank, 'multi_cell_tolerance_rate')
    config_dict['cell_min_margin'] = config.getint(bank, 'cell_min_margin')
    return config_dict