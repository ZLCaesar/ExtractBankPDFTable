import re
import fitz
import pdfplumber
from tqdm import tqdm
from package.extract_table.ExtractTableWithVerticalPoint import ExtractTableWithVerticalPoint
from package.extract_table.ExtractTableWithOnlyHorizontal import ExtractTableWithOnlyHorizontal
from package.extract_table.ExtractTableWithFullLine import ExtractTableWithFullLine
from package.toolkit.ExtractIndexFromContent import extract_index_from_content, extract_file_name
from package.toolkit import UnitRec
from package.config.Configure import get_config

class ExtractIndex:
    def __init__(self, pdf_file_path, index_list=[], bank_name=None):
        func_map = {
            "ZHAOSHANG": self.extarct_zs_table,
            "NINGBO": self.extarct_nb_table,
            "NANJING": self.extarct_nb_table,
            "JIANGSU": self.extarct_js_table,
            "PINGAN": self.extarct_js_table
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
        self.ur = UnitRec(self.args['unit_patterns'])

    def __combine_table(self, tables, top_line, bottom_line):
        for i in range(len(tables)-1):
            flag1, flag2, flag3 = False, False, True
            curr_table = tables[i]
            next_table = tables[i+1]
            if len(curr_table['data'].columns) == len(next_table['data'].columns):
                flag1 = True
            if abs(float(top_line)-float(next_table['top']))<self.args['combine_table_margin'] and abs(float(curr_table['bottom'])-float(bottom_line))<self.args['combine_table_margin']:
                flag2 = True
            for item in next_table['data'].iloc[0]:
                if item and re.findall('\d{4}年', item):
                    flag3 = False
                    break
            if flag1 and flag2 and flag3:
                tables[i+1]['data'] = tables[i]['data'].append(tables[i+1]['data']).reset_index(drop=True)
                tables[i+1]['page'] -= 1
                tables[i+1]['unit'] = tables[i]['unit']
            elif (not flag1) and flag2 and flag3:
                # 上下两个表的列数不一样，但是有可能是因为前一个表有合并单元格的情况
                if len(curr_table['data'])==1 and tables[i+1]['unit']==1:
                    tables[i+1]['unit'] = tables[i]['unit']
        return tables

    def valid_no_vertical_feat(self, no_vertical_feat, words_list):
        valid_list = []
        nb_lines = int(no_vertical_feat[0])
        if nb_lines == len(words_list):
            valid_list.append(True)
        else:
            return False
        for i in range(len(no_vertical_feat)-1):
            if no_vertical_feat[i+1]:
                if no_vertical_feat[i+1] in words_list[i]['text']:
                    valid_list.append(True)
                else:
                    return False
        return all(valid_list)

    def extract_index_from_text(self, index_list, text_list):
        
        index_dict = {item: None for item in index_list}

        for text in text_list:
            if not index_list:
                break
            temp_index_dict = extract_index_from_content(index_list, text)
            for item in temp_index_dict:
                index_dict[item] = temp_index_dict[item]
                index_list = [key for key in index_dict if index_dict[key] is None]
                # covert_text_num
        index_dict = {item: self.ur.covert_text_num(index_dict.get(item)) for item in index_dict}
        return index_dict

    def extarct_zs_table(self):
        etwnv = ExtractTableWithVerticalPoint(self.args)
        
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
        etwnv = ExtractTableWithVerticalPoint(self.args)
        etwon = ExtractTableWithOnlyHorizontal(self.args)

        ret_tables = []
        text_list = []
        top_line = 0
        bottom_line = 10000
        no_vertical_page = len(self.pdf.pages)
        for pid in tqdm(range(len(self.pdf.pages))):
            if self.use_fitz:
                page_mu = self.pdf_mu.loadPage(pid)
            else:
                page_mu = None
            page = self.pdf.pages[pid]
            words_list = etwnv.get_page_words(page, page_mu)
            content = ''.join([item['text'] for item in words_list])
            text_list.append(content.replace(" ",""))
            if self.valid_no_vertical_feat(self.args['no_vertical_feat'], words_list):
                no_vertical_page = pid
                print('no_vertical_page', no_vertical_page)
            if pid<no_vertical_page:
                tables, top_line_y, bottom_line_y = etwnv.get_table_by_page(page, words_list)
            else:
                tables, top_line_y, bottom_line_y = etwon.get_table_by_page(page, words_list)
            top_line = max(top_line, top_line_y)
            bottom_line = min(bottom_line, bottom_line_y)
            tables = [{'data': etwnv.drop_duplicate_cols(t['data']), 'unit':t['unit'], 'top': t['top'], 'bottom': t['bottom'], 'page':pid} for t in tables]
            
            ret_tables += tables
        index_list = self.index_list[:]
        index_dict = self.extract_index_from_text(index_list, text_list)
        print('top_line:', top_line)
        print('bottom_line:', bottom_line)
        ret_tables = self.__combine_table(ret_tables, top_line, bottom_line)
        self.ret['table'] = ret_tables
        self.ret['textQuota'] = index_dict
        return self.ret

    def __detect_lastline_unit(self, words_list):
        count = 0
        for i in range(len(words_list)-1, -1, -1):
            count += 1
            if count > 6:
                return None
            unit_feat, unit = self.ur.extract_unit(words_list[i]['text'])
            if unit_feat:
                return unit

        return None

    def extarct_js_table(self):
        etwfl = ExtractTableWithFullLine(self.args)
        etwon = ExtractTableWithOnlyHorizontal(self.args)

        ret_tables = []
        text_list = []
        top_line = 0
        bottom_line = 10000
        no_vertical_page = len(self.pdf.pages)
        last_page_unit = None
        for pid in tqdm(range(len(self.pdf.pages))):
            if self.use_fitz:
                page_mu = self.pdf_mu.loadPage(pid)
            else:
                page_mu = None
            page = self.pdf.pages[pid]
            words_list = etwfl.get_page_words(page, page_mu)
            content = ''.join([item['text'] for item in words_list])
            text_list.append(content.replace(" ",""))
            if self.valid_no_vertical_feat(self.args['no_vertical_feat'], words_list):
                no_vertical_page = pid
                print('no_vertical_page', no_vertical_page)
            if pid<no_vertical_page:
                tables, top_line_y, bottom_line_y = etwfl.get_table_by_page(page, words_list)
                if last_page_unit and tables and tables[0]['unit'] == 1:
                    tables[0]['unit'] = last_page_unit
            else:
                tables, top_line_y, bottom_line_y = etwon.get_table_by_page(page, words_list)
            
            top_line = max(top_line, top_line_y)
            bottom_line = min(bottom_line, bottom_line_y)
            tables = [{'data': etwfl.drop_duplicate_cols(t['data']), 'unit':t['unit'], 'top': t['top'], 'bottom': t['bottom'], 'page':pid} for t in tables]
            last_page_unit = self.__detect_lastline_unit(words_list)
            ret_tables += tables
        index_list = self.index_list[:]
        index_dict = self.extract_index_from_text(index_list, text_list)
        
        print('top_line:', top_line)
        print('bottom_line:', bottom_line)
        ret_tables = self.__combine_table(ret_tables, top_line, bottom_line)
        self.ret['table'] = ret_tables
        self.ret['textQuota'] = index_dict
        return self.ret
