import re
import fitz
import pdfplumber
from tqdm import tnrange, tqdm
from package.extract_table.ExtractTableWithVerticalPoint import ExtractTableWithVerticalPoint
from package.extract_table.ExtractTableWithOnlyHorizontal import ExtractTableWithOnlyHorizontal
from package.toolkit.ExtractIndexFromContent import extract_index_from_content, extract_file_name
from package.toolkit import UnitRec
from package.config.Configure import get_config

class ExtractIndex:
    def __init__(self, pdf_file_path, bank_name=None, index_list=[]):
        func_map = {
            "ZHAOSHANG": self.extarct_zs_table,
            "NINGBO": self.extarct_nb_table,
            "NANJING": self.extarct_zs_table
        }
        self.index_list = index_list
        self.ret = extract_file_name(pdf_file_path)
        if bank_name:
            self.args = get_config(bank_name)
        elif self.ret['bank']:
            self.args = get_config(self.ret['bank'])
        else:
            raise ValueError("Cannot find any bank name!")
        self.use_fitz = self.args['use_fitz']
        self.pdf = pdfplumber.open(pdf_file_path)
        if self.use_fitz:
            self.pdf_mu = fitz.open(pdf_file_path)

        self.extarct_table = func_map.get(self.args['bank_name'])

    def __combine_table(self, tables, top_line, bottom_line):
        for i in range(len(tables)-1):
            flag1, flag2, flag3 = False, False, True
            curr_table = tables[i]
            next_table = tables[i+1]
            if len(curr_table['data'].columns) == len(next_table['data'].columns):
                flag1 = True
            if abs(float(top_line)-float(next_table['top']))<15 and abs(float(curr_table['bottom'])-float(bottom_line))<15:
                flag2 = True
            for item in next_table['data'].iloc[0]:
                if item and re.findall('\d{4}年', item):
                    flag3 = False
                    break
            if flag1 and flag2 and flag3:
                tables[i+1]['data'] = tables[i]['data'].append(tables[i+1]['data']).reset_index(drop=True)
                tables[i+1]['page'] -= 1
                tables[i+1]['unit'] = tables[i]['unit']
        return tables

    def extract_index_from_text(self, index_list, text_list):
        ur = UnitRec()
        index_dict = {item: None for item in index_list}

        for text in text_list:
            if not index_list:
                break
            temp_index_dict = extract_index_from_content(index_list, text)
            for item in temp_index_dict:
                index_dict[item] = temp_index_dict[item]
                index_list = [key for key in index_dict if index_dict[key] is None]
                # covert_text_num
        index_dict = {item: ur.covert_text_num(index_dict.get(item)) for item in index_dict}
        return index_dict

    def extarct_zs_table(self):
        etwnv = ExtractTableWithVerticalPoint(CURVES_MIN_MARGIN=self.args['curves_min_margin'],
                                    MAX_ADJACENT_DIS=self.args['max_adjacent_dis'],
                                    UP_DEVIATION_TOLERANCE=self.args['up_deviation_tolerance'], 
                                    DOWN_DEVIATION_TOLERANCE=self.args['down_deviation_tolerance'],
                                    UNDER_THIS = self.args['under_this'],
                                    START_FROM_THIS = self.args['start_from_this'],
                                    ABOVE_THIS = self.args['above_this'],
                                    BOUND_FLAG_DIS_TOLERANCE = self.args['bound_flag_dis_tolerance'])
        
        ret_tables = []
        text_list = []
        top_line = 0
        bottom_line = 10000
        for pid in tqdm(range(len(self.pdf.pages))):
            if self.use_fitz:
                page_mu = self.pdf_mu.loadPage(pid)
            else:
                page_mu = None
            page = self.pdf.pages[pid]
            words_list = etwnv.get_page_words(page, page_mu)
            content = ''.join([item['text'] for item in words_list])
            text_list.append(content.replace(" ",""))
            tables, top_line_y, bottom_line_y = etwnv.get_table_by_page(page, words_list)
            top_line = max(top_line, top_line_y)
            bottom_line = min(bottom_line, bottom_line_y)
            tables = [{'data': etwnv.drop_duplicate_cols(t['data']), 'unit':t['unit'], 'top': t['top'], 'bottom': t['bottom'], 'page':pid} for t in tables]
            
            ret_tables += tables
        index_list = self.index_list[:]
        index_dict = self.extract_index_from_text(index_list, text_list)
        ret_tables = self.__combine_table(ret_tables, top_line, bottom_line)
        self.ret['table'] = ret_tables
        self.ret['textQuota'] = index_dict
        return self.ret

    def extarct_nb_table(self):
        etwnv = ExtractTableWithVerticalPoint(CURVES_MIN_MARGIN=self.args['curves_min_margin'],
                                    CELL_MIN_MARGIN=self.args['cell_min_margin'],
                                    MAX_ADJACENT_DIS=self.args['max_adjacent_dis'],
                                    UNDER_THIS = self.args['under_this'],
                                    START_FROM_THIS = self.args['start_from_this'],
                                    ABOVE_THIS = self.args['above_this'],
                                    BOUND_FLAG_DIS_TOLERANCE = self.args['bound_flag_dis_tolerance'],
                                    MULTI_CELL_TOLERANCE_RATE = self.args['multi_cell_tolerance_rate'])
        etwon = ExtractTableWithOnlyHorizontal(CURVES_MIN_MARGIN=self.args['curves_min_margin'],
                                    MAX_ADJACENT_DIS=self.args['max_adjacent_dis'],
                                    UNDER_THIS = self.args['under_this'],
                                    START_FROM_THIS = self.args['start_from_this'],
                                    ABOVE_THIS = self.args['above_this'],
                                    BOUND_FLAG_DIS_TOLERANCE = self.args['bound_flag_dis_tolerance'])

        ret_tables = []
        text_list = []
        top_line = 0
        bottom_line = 10000
        for pid in tqdm(range(len(self.pdf.pages))):
            if self.use_fitz:
                page_mu = self.pdf_mu.loadPage(pid)
            else:
                page_mu = None
            page = self.pdf.pages[pid]
            words_list = etwnv.get_page_words(page, page_mu)
            content = ''.join([item['text'] for item in words_list])
            text_list.append(content.replace(" ",""))
            if pid<self.args['no_vertical_page']:
                tables, top_line_y, bottom_line_y = etwnv.get_table_by_page(page, words_list)
            else:
                tables, top_line_y, bottom_line_y = etwon.get_table_by_page(page, words_list)
            top_line = max(top_line, top_line_y)
            bottom_line = min(bottom_line, bottom_line_y)
            tables = [{'data': etwnv.drop_duplicate_cols(t['data']), 'unit':t['unit'], 'top': t['top'], 'bottom': t['bottom'], 'page':pid} for t in tables]
            
            ret_tables += tables
        index_list = self.index_list[:]
        index_dict = self.extract_index_from_text(index_list, text_list)

        ret_tables = self.__combine_table(ret_tables, top_line, bottom_line)
        self.ret['table'] = ret_tables
        self.ret['textQuota'] = index_dict
        return self.ret
