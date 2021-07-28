import fitz
import pdfplumber
from tqdm import tqdm
from package.ExtractTable import ExtractTableWithNoVertical

def extarct_zh_table(pdf_file_path, table_type_change_page=90):
    pdf = pdfplumber.open(pdf_file_path)
    pdf_mu = fitz.open(pdf_file_path)

    etwnv = ExtractTableWithNoVertical()


    dic = {}
    for pid in tqdm(range(pdf_mu.pageCount)):
        page = pdf_mu.loadPage(pid)
        words_list = etwnv.get_words_from_pymupdf(page)
        page = pdf.pages[pid]
        for i in range(len(words_list)):
            words_list[i]['top'] = float(page.height)- words_list[i]['top']
            words_list[i]['bottom'] = float(page.height) - words_list[i]['bottom']
            words_list[i]['x0'] = words_list[i]['x0'] + 1
            words_list[i]['x1'] = words_list[i]['x1'] - 1
        tables = etwnv.get_table_by_page(page, words_list)
        if pid>table_type_change_page:
            tables = [etwnv.drop_duplicate_cols(t) for t in tables]
        dic[pid] = tables

    return dic