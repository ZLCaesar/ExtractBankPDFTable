import fitz
import pdfplumber
from tqdm import tqdm
from package.extract_table.ExtractTableWithVerticalPoint import ExtractTableWithVerticalPoint

def extarct_zh_table(pdf_file_path):
    pdf = pdfplumber.open(pdf_file_path)
    pdf_mu = fitz.open(pdf_file_path)
    etwnv = ExtractTableWithVerticalPoint()
    ret_tables = []
    for pid in tqdm(range(pdf_mu.pageCount)):
        page_mu = pdf_mu.loadPage(pid)
        
        page = pdf.pages[pid]
        words_list = etwnv.get_page_words(page, page_mu)
        tables = etwnv.get_table_by_page(page, words_list)
        tables = [{'data': etwnv.drop_duplicate_cols(t['data']), 'unit':t['unit'], 'page':pid} for t in tables]
        
        ret_tables += tables

    return ret_tables