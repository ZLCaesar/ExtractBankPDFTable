import fitz
import pdfplumber
from tqdm import tqdm
from package.ExtractTable import ExtractTableWithNoVertical

def extarct_zh_table(pdf_file_path):
    pdf = pdfplumber.open(pdf_file_path)
    pdf_mu = fitz.open(pdf_file_path)

    etwnv = ExtractTableWithNoVertical()


    ret_tables = []
    for pid in tqdm(range(pdf_mu.pageCount)):
        page = pdf_mu.loadPage(pid)
        words_list = etwnv.get_words_from_pymupdf(page)
        page = pdf.pages[pid]
        for i in range(len(words_list)):
            words_list[i]['top'] = float(page.height)- words_list[i]['top']
            words_list[i]['bottom'] = float(page.height) - words_list[i]['bottom']
            words_list[i]['x0'] = words_list[i]['x0'] + 1
            words_list[i]['x1'] = words_list[i]['x1'] - 1
        words_list = sorted(words_list, key=lambda x:x['top'], reverse=True)
        tables = etwnv.get_table_by_page(page, words_list)
        tables = [{'data': etwnv.drop_duplicate_cols(t['data']), 'unit':t['unit'], 'page':pid} for t in tables]
        
        ret_tables += tables

    return ret_tables