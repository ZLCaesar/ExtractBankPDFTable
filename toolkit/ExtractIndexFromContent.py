import re

num_pattern = '([\d,%\.]+[十百千万亿]*)'
maps = {
    "第一季度": 'Q1',
    "第二季度": 'Q2',
    "第三季度": 'Q3',
    "第四季度": 'Q4',
    "半年": 'Q2',
    "年": 'Q4'
}
def extract_file_name(file_name):
    parts = file_name.split('/')
    if len(parts)>1:
        file_name = parts[-1]
    pattern = '(.*银行)(\d+)年?([第一二三四季度半年Q\d]+)'
    info = re.findall(pattern, file_name)
    ret = {'bank': None, 'year': None, 'quarter': None}
    if info and len(info[0])==3:
        ret['bank'] = info[0][0]
        ret['year'] = info[0][1]
        ret['quarter'] = maps.get(info[0][2], info[0][2])
        return ret

    return ret

def recombination(find_dict):
    if not find_dict:
        return []
    temp = []
    sub_temp = [[find_dict[0][0], 1]]
    for i in range(1, len(find_dict)):
        if find_dict[i][1][0]-find_dict[i-1][1][0] < 1:   #形如‘中长期贷款平均余额26,139.58亿元，利息收入612.94亿元’
            sub_temp.append([find_dict[i][0], 0])
        elif find_dict[i][1][0]-find_dict[i-1][1][1]<4:
            sub_temp.append([find_dict[i][0], 1])
        else:
            temp.append(sub_temp)
            sub_temp = [[find_dict[i][0], 1]]
    if sub_temp:
        temp.append(sub_temp)
        
    return temp

def extract_index_from_content(index_list, text):
    ret_dict = {}
    find_dict = {}
    inner = '.{0,50}?'
    for index in index_list:
        pattern = inner.join(index)
        regex = re.compile(pattern)
        match = regex.search(text)
        if match:
#             print(match)
            s, e = match.start(), match.end()
#             if (e-s)/len(index)>2:
#                 continue
            find_dict[index] = [s, e, pattern]

    find_dict = sorted(find_dict.items(), key=lambda x:x[1][0])
    find_dict = recombination(find_dict)

    if len(find_dict) == 1 and len(find_dict[0]) == 1:
        index = find_dict[0][0][0]  #第一行，第一个，0元素
        value = re.findall(inner.join(index)+'.{0,4}?'+num_pattern, text)
        if value:
            ret_dict[index] = value[0]

    elif len(find_dict) >= 1:
        for item in find_dict:
            nb_index = len(item)
            pattern = [inner.join(index[0]) for index in item if index[1]]
            pattern = pattern[0]+inner+inner.join([num_pattern for _ in range(nb_index)])
            values = re.findall(pattern, text)
            for i in range(len(item)):
                ret_dict[item[i][0]] = values[0][i]
                    
    return ret_dict