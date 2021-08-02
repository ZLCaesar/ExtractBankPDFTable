# ExtractBankPDFTable

## 使用方法

from ExtractBankPDFTable import extarct_zh_table

ret_list = extarct_zh_table('xxxx.pdf', index_list)

## 返回
ret_list是个list，里面的元素是dict：
- 'year':'2020',
- 'quarter':'Q2',
- 'bank':'招商银行',
- 'table':[{'data': dataframe,'unit':1}{}],
- 'textQuota': {'quota1':, 'quota2':}
