import re
from typing import Pattern
import fitz
import pdfplumber
from tqdm import tqdm
import pandas as pd
from package.extract_table.ExtractTableWithVerticalPoint import ExtractTableWithVerticalPoint
from package.extract_table.ExtractTableWithOnlyHorizontal import ExtractTableWithOnlyHorizontal
from package.extract_table.ExtractTableWithFullLine import ExtractTableWithFullLine
from package.toolkit.ExtractIndexFromContent import extract_index_from_content, extract_file_name
from package.toolkit import UnitRec
from package.config.Configure import get_config


class ExtractIndex:
    def __init__(self, pdf_file_path, index_list=[], bank_name=None):
        """
        extarct_table_type1 :表格类型——完整表格+只有上下横线
        extarct_table_type2 :表格类型——缺少垂直线+只有上下横线
        extarct_table_type3 :表格类型——只有上下横线
        extarct_table_type4 :表格类型——缺少垂直线
        extarct_table_type5 :专门特殊处理中信银行
        extarct_table_type6 :专门特殊处理华夏银行
        """
        
        func_map = {
            "ZHAOSHANG": self.extarct_table_type4,
            "JIAOTONG": self.extarct_table_type3,
            "NINGBO": self.extarct_table_type2,
            "NANJING": self.extarct_table_type2,
            "JIANGSU": self.extarct_table_type1,
            "PINGAN": self.extarct_table_type1,
            "ZHONGXIN": self.extarct_table_type5,
            "PUFA": self.extarct_table_type2,
            "GUANGDA": self.extarct_table_type1,
            "HUAXIA": self.extarct_table_type6,
            "MINSHENG": self.extarct_table_type1,
            "XINGYE": self.extarct_table_type1,
            "SHANGHAI": self.extarct_table_type1,
            "ZHESHANG": self.extarct_table_type1,
            "BEIJING": self.extarct_table_type1,
            "GONGSHANG": self.extarct_table_type2,
            "YOUCHU": self.extarct_table_type1,
            "JIANSHE": self.extarct_table_type2,
            "ZHONGHANG": self.extarct_table_type1,
            "NONGHANG": self.extarct_table_type3,
            "XIAMEN": self.extarct_table_type1
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
                if item and re.findall('\d{4}年', str(item)):
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

            if self.args.get('get_unit_from_last_table', False) and next_table.get('unit_feat') is None and curr_table.get('unit_feat') is not None:
                tables[i+1]['unit'] = tables[i]['unit']
                tables[i+1]['unit_feat'] = tables[i].get('unit_feat', None)
        return tables

    # def valid_no_vertical_feat(self, no_vertical_feat, words_list):
    #     valid_list = []
    #     nb_lines = int(no_vertical_feat[0])
    #     if nb_lines == len(words_list):
    #         valid_list.append(True)
    #     else:
    #         return False
    #     for i in range(len(no_vertical_feat)-1):
    #         if no_vertical_feat[i+1]:
    #             if no_vertical_feat[i+1] in words_list[i]['text']:
    #                 valid_list.append(True)
    #             else:
    #                 return False
    #     return all(valid_list)

    def valid_no_vertical_feat(self, no_vertical_feat, words_list):
        
        bank_name = no_vertical_feat[0]
        pattern = no_vertical_feat[1]
        if not words_list:
            return False
        if self.args.get('no_vertical_feat2_maxlen', None):
            if len(words_list)>self.args.get('no_vertical_feat2_maxlen'):
                return False
        if bank_name in words_list[0]['text']:
            for i in range(1, min(len(words_list),self.args.get('no_vertical_max_nbline', 20))):
                info = re.findall(pattern, words_list[i]['text'])
                if info:
                    return True

        return False

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

    def extarct_jt_table(self):
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
            words_list = etwon.get_page_words(page, page_mu)
            content = ''.join([item['text'] for item in words_list])
            text_list.append(content.replace(" ",""))
            tables, top_line_y, bottom_line_y = etwon.get_table_by_page(page, words_list)
            top_line = max(top_line, top_line_y)
            bottom_line = min(bottom_line, bottom_line_y)
            tables = [{'data': etwon.drop_duplicate_cols(t['data']), 'unit':t['unit'], 'top': t['top'], 'bottom': t['bottom'], 'page':pid} for t in tables]
            
            ret_tables += tables
        index_list = self.index_list[:]
        index_dict = self.extract_index_from_text(index_list, text_list)
        print('top_line:', top_line)
        print('bottom_line:', bottom_line)
        ret_tables = self.__combine_table(ret_tables, top_line, bottom_line)
        self.ret['table'] = ret_tables
        self.ret['textQuota'] = index_dict
        return self.ret

    def extarct_table_type3(self):
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
            words_list = etwon.get_page_words(page, page_mu)
            content = ''.join([item['text'] for item in words_list])
            text_list.append(content.replace(" ",""))
            tables, top_line_y, bottom_line_y = etwon.get_table_by_page(page, words_list)
            top_line = max(top_line, top_line_y)
            bottom_line = min(bottom_line, bottom_line_y)
            tables = [{'data': etwon.drop_duplicate_cols(t['data']), 'unit':t['unit'], 'top': t['top'], 'bottom': t['bottom'], 'page':pid} for t in tables]
            
            ret_tables += tables
        index_list = self.index_list[:]
        index_dict = self.extract_index_from_text(index_list, text_list)
        print('top_line:', top_line)
        print('bottom_line:', bottom_line)
        ret_tables = self.__combine_table(ret_tables, top_line, bottom_line)
        self.ret['table'] = ret_tables
        self.ret['textQuota'] = index_dict
        return self.ret

    def extarct_table_type4(self):
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

    def extarct_table_type2(self):
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
                tables, top_line_y, bottom_line_y = etwnv.get_table_by_page(page, words_list, self.args['drop_first_line'])
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

    def extarct_table_type1(self):
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
                top_line = max(top_line, top_line_y)
                bottom_line = min(bottom_line, bottom_line_y)
            else:
                tables, _, _ = etwon.get_table_by_page(page, words_list, self.args.get('replace_short_line', False))
            
            
            tables = [{'data': etwfl.drop_duplicate_cols(t['data']), 'unit':t['unit'], 'top': t['top'], 'bottom': t['bottom'], 'page':pid} for t in tables]
            last_page_unit = self.__detect_lastline_unit(words_list)
            ret_tables += tables
        index_list = self.index_list[:]
        index_dict = self.extract_index_from_text(index_list, text_list)
        bottom_line = max(bottom_line, 0)
        print('top_line:', top_line)
        print('bottom_line:', bottom_line)
        ret_tables = self.__combine_table(ret_tables, top_line, bottom_line)
        self.ret['table'] = ret_tables
        self.ret['textQuota'] = index_dict
        return self.ret

    def extarct_table_type5(self):
        def split_row(table):
            # 因为有些有“-”的行，傻逼pdfplumber合并到上一行去了,
            # 只对第一列有此种情况的表进行处理
            add_memory = []
            nb_col = len(table.columns)
            for i, item in enumerate(table.iloc[:,0]):
                
                if item and not item.startswith('–') and item.count('–') == 1:
                    item = item.strip()
                    parts = item.split('–')
                    new_line = [parts[0]]+[None for _ in range(nb_col-1)]
                    table.iloc[i, 0] = '–'+parts[1]
                    add_memory.append([i, new_line])
            if add_memory:
                for item in reversed(add_memory):
                    
                    table = pd.concat([table.loc[:item[0]-1], pd.DataFrame([item[1]]), table.loc[item[0]:]],ignore_index=True)
                    
            return table

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
                tables, top_line_y, bottom_line_y = etwnv.get_table_by_page(page, words_list, self.args['drop_first_line'])
            else:
                tables, top_line_y, bottom_line_y = etwon.get_table_by_page(page, words_list)
            top_line = max(top_line, top_line_y)
            bottom_line = min(bottom_line, bottom_line_y)
            tables = [{'data': etwnv.drop_duplicate_cols(t['data']), 'unit':t['unit'], 'top': t['top'], 'bottom': t['bottom'], 'page':pid} for t in tables]
            tables = [{'data': split_row(t['data']), 'unit':t['unit'], 'top': t['top'], 'bottom': t['bottom'], 'page':pid} for t in tables]
            ret_tables += tables
        index_list = self.index_list[:]
        index_dict = self.extract_index_from_text(index_list, text_list)
        print('top_line:', top_line)
        print('bottom_line:', bottom_line)
        ret_tables = self.__combine_table(ret_tables, top_line, bottom_line)
        self.ret['table'] = ret_tables
        self.ret['textQuota'] = index_dict
        return self.ret

    def extarct_table_type6(self):
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
                tables, top_line_y, bottom_line_y = etwon.get_table_by_page(page, words_list, self.args.get('replace_short_line', False))
            
            top_line = max(top_line, top_line_y)
            bottom_line = min(bottom_line, bottom_line_y)
            tables = [{'data': etwfl.drop_duplicate_cols(t['data']), 'unit':t['unit'], 'top': t['top'], 'bottom': t['bottom'], 'page':pid} for t in tables]
            last_page_unit = self.__detect_lastline_unit(words_list)
            ret_tables += tables
        index_list = self.index_list[:]
        index_dict = self.extract_index_from_text(index_list, text_list)
        bottom_line = max(bottom_line, 0)
        print('top_line:', top_line)
        print('bottom_line:', bottom_line)
        ret_tables = self.__combine_table(ret_tables, top_line, bottom_line)
        self.ret['table'] = ret_tables
        self.ret['textQuota'] = index_dict
        return self.ret