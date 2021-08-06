import fitz
import pdfplumber
from tqdm import tqdm
from package.extract_table.ExtractTableWithVerticalPoint import ExtractTableWithVerticalPoint
from package.extract_table.ExtractTableWithOnlyHorizontal import ExtractTableWithOnlyHorizontal
from package.toolkit.ExtractIndexFromContent import extract_index_from_content, extract_file_name
from package.toolkit import UnitRec
from package.config.Configure import get_config

class ExtractIndex:
    def __init__(self, pdf_file_path, index_list, bank_name=None):
        func_map = {
            "ZHAOSHANG": self.extarct_zh_table,
            "NINGBO": self.extarct_nb_table
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

    def extarct_zh_table(self, UP_DEVIATION_TOLERANCE, DOWN_DEVIATION_TOLERANCE):
        etwnv = ExtractTableWithVerticalPoint(UP_DEVIATION_TOLERANCE=UP_DEVIATION_TOLERANCE, DOWN_DEVIATION_TOLERANCE=DOWN_DEVIATION_TOLERANCE)
        
        ret_tables = []
        text_list = []
        for pid in tqdm(range(len(self.pdf.pages))):
            if self.use_fitz:
                page_mu = self.pdf_mu.loadPage(pid)
            else:
                page_mu = None
            page = self.pdf.pages[pid]
            words_list = etwnv.get_page_words(page, page_mu)
            content = ''.join([item['text'] for item in words_list])
            text_list.append(content.replace(" ",""))
            tables = etwnv.get_table_by_page(page, self.args['under_this'], self.args['start_from_this'], self.args['above_this'], words_list)
            tables = [{'data': etwnv.drop_duplicate_cols(t['data']), 'unit':t['unit'], 'page':pid} for t in tables]
            
            ret_tables += tables
        index_list = self.index_list[:]
        index_dict = self.extract_index_from_text(index_list, text_list)

        self.ret['table'] = ret_tables
        self.ret['textQuota'] = index_dict
        return self.ret

    def extarct_nb_table(self):
        etwnv = ExtractTableWithVerticalPoint()
        etwon = ExtractTableWithOnlyHorizontal()

        ret_tables = []
        text_list = []
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
                tables = etwnv.get_table_by_page(page, self.args['under_this'], self.args['start_from_this'], self.args['above_this'], words_list)
            else:
                tables = etwon.get_table_by_page(page, self.args['under_this'], self.args['start_from_this'], self.args['above_this'], words_list)
            tables = [{'data': etwnv.drop_duplicate_cols(t['data']), 'unit':t['unit'], 'page':pid} for t in tables]
            
            ret_tables += tables
        index_list = self.index_list[:]
        index_dict = self.extract_index_from_text(index_list, text_list)

        self.ret['table'] = ret_tables
        self.ret['textQuota'] = index_dict
        return self.ret
