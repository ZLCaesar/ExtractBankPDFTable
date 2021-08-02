import fitz
import pdfplumber
from tqdm import tqdm
from package.extract_table.ExtractTableWithVerticalPoint import ExtractTableWithVerticalPoint
from package.toolkit.ExtractIndexFromContent import extract_index_from_content, extract_file_name
from package.toolkit import UnitRec

def extract_index_from_text(index_list, text_list):
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

# def extract_index_from_text(index_list, text_list):
#     index_dict = {}

#     for text in text_list:
#         temp_index_dict = extract_index_from_content(index_list, text)
#         for item in temp_index_dict:
#             temp = index_dict.get(item, [])
#             temp.append(temp_index_dict[item])
#             index_dict[item] = temp

#     return index_dict

def extarct_zh_table(pdf_file_path, index_list):
    pdf = pdfplumber.open(pdf_file_path)
    pdf_mu = fitz.open(pdf_file_path)
    etwnv = ExtractTableWithVerticalPoint()
    ret_tables = []
    text_list = []
    for pid in tqdm(range(pdf_mu.pageCount)):
        page_mu = pdf_mu.loadPage(pid)
        
        page = pdf.pages[pid]
        words_list = etwnv.get_page_words(page, page_mu)
        content = ''.join([item['text'] for item in words_list])
        text_list.append(content.replace(" ",""))
        tables = etwnv.get_table_by_page(page, words_list)
        tables = [{'data': etwnv.drop_duplicate_cols(t['data']), 'unit':t['unit'], 'page':pid} for t in tables]
        
        ret_tables += tables

    index_dict = extract_index_from_text(index_list, text_list)
    ret = extract_file_name(pdf_file_path)
    ret['table'] = ret_tables
    ret['textQuota'] = index_dict
    return ret