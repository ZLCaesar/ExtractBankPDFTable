# ExtractBankPDFTable

## 使用方法

from package import ExtractIndex

pdf_file_path = '../data/宁波银行2020半年度报告.pdf'

bank_name = '宁波银行'

et = ExtractIndex(pdf_file_path, index_list, bank_name)

result = et.extarct_table()

pdf文件名命名规范为：
- XXX银行XXXX年报告期.pdy
-- 例如：宁波银行2020年第一季度财报.pdf
- 无中文形式
-- 例如： NINGBO2020Q1.pdf

## 返回
ret_list是个list，里面的元素是dict：
- 'year':'2020',
- 'quarter':'Q2',
- 'bank':'招商银行',
- 'table':[{'data': dataframe,'unit':1}{}],
- 'textQuota': {'quota1':, 'quota2':}
