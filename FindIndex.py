import time

def find_recent_year_column(table, now_year=None):
    if not now_year:
        now_year = str(time.localtime().tm_year)+'年'
    
    for i, row in table.iterrows():
        for j in row.index:
            item = str(table.iloc[i, j])
            if now_year in item:
                return i, j 
        if i > 3:
            break
            
    return -1, -1

def get_index(table, year_column, index_name_column=0):
    """对初步抽取的数据进行整理，如果pair对中没有值：
        1. cell中的换行，需要进一步处理，暂时不做
        2. 删除（现行办法）

    Args:
        result ([type]): [description]
    """
    result = []
    for i, row in table.iterrows():
        index_name=row[index_name_column]
        index = row[year_column]

        if index_name and index:
            result.append((index_name, index))
    
    return result

