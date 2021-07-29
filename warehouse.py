    """写完代码但是由于各种原因没有被用到的代码，暂时放在这里
    """
import numpy as np
MAX_SPACE_HEIGHT = 40
def get_bound(page):
    """获取表之间的边界。根据水平线结点的x是否相同来判断其是否属于同一张表。详见readme.md

    Args:
        page ([type]): [description]
    """
    def compare_set(set1, set2):
        count = 0
        thred = min(len(set1), len(set2))
        for x in set1:
            for y in set2:
                if abs(x-y)<1:
                    count += 1
                if count == thred:
                    return True
        return False
    
    memory_dict = {}
    for he in page.horizontal_edges:
        x0 = he['x0']
        y0 = he['y0']
        x1 = he['x1']     
        add_flag = False
        for y_ in memory_dict:
            if abs(y0-y_)<1:  #认为是同一个y
                x_set = memory_dict.get(y_)
                x_set.add(x0)
                x_set.add(x1)
                memory_dict[y_] = x_set
                add_flag = True
        if not add_flag:
            x_set = set()
            x_set.add(x0)
            x_set.add(x1)
            memory_dict[y0] = x_set
    
    before_set = set()
    table_id = 0
    table_id_list = []
    for y in memory_dict:
        x_set = memory_dict.get(y)
        if before_set:
            if compare_set(before_set, x_set):
                table_id_list.append(table_id)
            else:
                table_id += 1
                table_id_list.append(table_id)
            before_set = x_set
        else:
            table_id_list.append(table_id)
            before_set = x_set
            
    return table_id_list


def get_table_boundary(y_split, max_space_height=None):
    """
    一个页面可能有多个表格，根据纵坐标判断分了几个表格
    """
    if not max_space_height:
        max_space_height = MAX_SPACE_HEIGHT
    table_id = 0
    table_boundary = {}
    if len(y_split)==0:
        return {}
    y = sorted(y_split, reverse=True)
    spaces = np.diff(y)
    begin = 0
    end = 0
    for i in range(len(spaces)):
        end = i
        if abs(spaces[i]) > max_space_height:
            if begin != end:
                table_boundary[table_id] = [y[begin]+1, y[end]-1, begin, end]
                table_id+=1
            begin = end+1
    
    if table_id not in table_boundary and end>begin:
        table_boundary[table_id] = [y[begin]+1, y[end+1]-1, begin, end+1]
        
    return table_boundary