# ExtractBankPDFTable

## 使用方法

from ExtractBankPDFTable import extarct_zh_table
table_dicts = extarct_zh_table('xxxx.pdf')

## 返回
table_dicts是个字典，key是页码，value是个list，即如果该页面有多个表，以list的形式返回，表以pandas.DataFrame形式保存。
