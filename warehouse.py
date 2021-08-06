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

def valid(self, xs, ys):
    """xs和ys是根据字典value(list)的元素个数进行降序排序之后得到的list。
    xs[0][0]就是在某个水平线上，拥有分割点最多的ym，则其很有可能是上下边界
    然后再去遍历ys中每个元素的第1项，即[y1, y2, ..., yn]，如果有ym～=yn，则认为找到了基准线

    Args:
        xs (list): [(y1, [x11, x12, ..., x1n]), (y2, [x21, x22, ..., x2n])]
        ys (list): [(x1, [y11, y12, ..., y1n]), (x2, [y21, y22, ..., y2n])]

    Returns:
        int: -1表示未找到，否则返回ys的索引
    """
    if len(xs)>0:
        most_x_line = xs[0][0]
    else:
        return -1
    for i in range(len(ys)):
        y = ys[i][1]
        exist_flag = False
        for _y in y:
            if abs(_y-most_x_line)<1:
                exist_flag = True
        if exist_flag:
            return i
        
    return -1
        
def find_first_last_line(self, horizontal_edges):
    """根据水平边界线，找到上下界。
    因为只有水平线，且没有明显的间隔断点用于明确列间隔，因此只能通过启发式规则确定表的上下边界。其基本思想为，隶属于同一张表

    Args:
        horizontal_edges (dict): 水平线，包含起始点的xy坐标

    Returns:
        Float: 上下边界
    """
    def iter_dict(k, v, dic):
        """循环更新生成字典。
        以key为x坐标，value为y坐标为例。
        key为x坐标，value为共享

        Args:
            k ([type]): [description]
            v ([type]): [description]
            dic ([type]): [description]

        Returns:
            [type]: [description]
        """
        if k in dic:
            temp = dic.get(k)
            temp.append(v)
            dic[k] = temp
        else:
            exist = False
            for k_ in dic:
                if abs(k_-k)<1:
                    temp = dic.get(k_)
                    temp.append(v)
                    dic[k_] = temp
                    exist = True
                    break
            if not exist:
                dic[k] = [v]
        return dic

    he_dict = {}
    ve_dict = {}
    for he in horizontal_edges:
        x, y = he['x0'], he['y0']
        ve_dict = iter_dict(y, x, ve_dict) #key为纵坐标，value为横坐标list
        he_dict = iter_dict(x, y, he_dict) #key为横坐标，value为纵坐标list
        
    xs = sorted(ve_dict.items(), key=lambda x:len(x[1]), reverse=True)
    ys = sorted(he_dict.items(), key=lambda x:len(x[1]), reverse=True)
    flag = self.valid(xs, ys)
    """
    如果flag返回的不是-1，则根据索引找到了上下边界，否则，则返回分割点最多的list，即ys[0]
    """
    if flag != -1:
        x, ys = ys[flag][0], ys[flag][1]
    else:
        x, ys = ys[0][0], ys[0][1]
    ys = sorted(ys, reverse=True)
    if len(ys)>1:
        return x, ys[0], ys[-1]
    return None, None, None