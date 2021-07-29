from re import I, S
import numpy as np
import pandas as pd
from .toolkit import UnitRec
from .deal_row_boundry import get_bound_by_flag, get_table_boundary, find_proper_rows

class ExtractTableWithNoVertical:
    def __init__(
        self, 
        CURVES_MIN_MARGIN=8, 
        MAX_SPACE_HEIGHT=40, 
        CELL_HEIGHT=25, 
        MORE_THAN_ONE_CELL_HEIGHT=28,
        MAX_ADJACENT_DIS=5):
        """抽取表格，适用的表格形式：
                1. 横竖线充足（约等于完美表格）
                2. 视觉上只有水平线，但有列分割结点（视觉上没有垂直线，但水平线按照列进行了分段）

        Args:
            CURVES_MIN_MARGIN (int, optional): 一个cell的上下距离如果没有超过此值，则不认为其是一条有效边界. Defaults to 8.
            MAX_SPACE_HEIGHT (int, optional): 用于确定表之间的边界，当边界大于此值时，认为不是同一张表. Defaults to 40.
            CELL_HEIGHT (int, optional): 一个表格CELL的高度. Defaults to 25.
            MORE_THAN_ONE_CELL_HEIGHT (int, optional): 如果两条水平线的高度差超过此值，则认为有合并单元格的存在. Defaults to 28.
            MAX_ADJACENT_DIS (int, optional): 在使用pymupdf解析pdf抽取文字时，有些视觉上相邻的字符串是抽取出来是断开的，如果两个在同一行上的字符
            串的首尾距离小于此值，则认为两者应该相连. Defaults to 5.
        """
        
        self.CURVES_MIN_MARGIN = CURVES_MIN_MARGIN
        self.MAX_SPACE_HEIGHT = MAX_SPACE_HEIGHT
        self.CELL_HEIGHT = CELL_HEIGHT
        self.MORE_THAN_ONE_CELL_HEIGHT = MORE_THAN_ONE_CELL_HEIGHT
        self.MAX_ADJACENT_DIS = MAX_ADJACENT_DIS
        self.unit_rec = UnitRec()

    def get_page_words(self, page):
        """
        转换每个字符的y坐标，使其与线坐标一致。（字符的y坐标其实位置在顶部，而线坐标的起始位置在底部）
        """
        height = page.height
        words = page.extract_words()
        for i in range(len(words)):
            words[i]['top'] = height - words[i]['top']
            words[i]['bottom'] = height - words[i]['bottom']
            
        return words

    def get_bound(self, page):
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
        
    def drop_duplicate_cols(self, table):
        """对抽取出来的表进行后处理。由于坐标细微误差，有可能导致多出来一列全None或者相同的两列，需要对其进行删除。
        方法为：相邻两列进行比较，如果后一列每行元素要么是None，要么与前一列相同，则该列为冗余列，删除。
        """
        i = 0
        while i < len(table.columns)-1:
            curr_col = list(table[i])
            next_col = list(table[i+1])
            cols = []
            temp = []
            for j in range(len(next_col)):
                if next_col[j] is None:
                    temp.append(True)
                elif next_col[j] == curr_col[j]:
                    temp.append(True)
                else:
                    temp.append(False)
            if all(temp):
                table = table.drop(i+1, axis=1)
                table.columns = list(range(len(table.columns)))
                i = 0
            else:
                i += 1
        return table

    def get_table_y(self, page):
        """
        获取每一行所在的纵坐标
        """
        y_split = set()
        if page.curves:
            for i in range(len(page.curves)):
                for item in page.curves[i]['pts']:
                    if not y_split:
                        y_split.add(item[1])
                    add_y_flag = True
                    for y in y_split:
                        if abs(y-item[1])<self.CURVES_MIN_MARGIN:
                            add_y_flag = False
                    if add_y_flag:
                        y_split.add(item[1])
        else:         
            for item in page.horizontal_edges:
                if not y_split:
                    y_split.add(item['y0'])
                    if abs(item['y1']-item['y0'])>self.CURVES_MIN_MARGIN:
                        y_split.add(item['y1'])
                
                    y_split.add(item['y1'])

                add_y0_flag = True
                add_y1_flag = True
                for y in y_split:
                    if abs(y-item['y0'])<self.CURVES_MIN_MARGIN:
                        add_y0_flag = False
                for y in y_split:
                    if abs(y-item['y1'])<self.CURVES_MIN_MARGIN:
                        add_y1_flag = False
                if add_y0_flag:
                    y_split.add(item['y0'])
                if add_y1_flag:
                    y_split.add(item['y1'])
        # table_id_list = self.get_bound(page)         
        return y_split

    def get_table_x(self, page, y_range=[]):
        """
        获取每一列的横坐标
        """
        x_split = set()
        if page.curves:
            for i in range(len(page.curves)):
                for item in page.curves[i]['pts']:
                    if y_range and (y_range[-1]>item[1] or item[1]>y_range[0]):
                        continue
                    if not x_split:
                        x_split.add(item[0])
                    add_x_flag = True
                    pop_item = None
                    for x in x_split:
                        if abs(x-item[0])<self.CURVES_MIN_MARGIN:
                            add_x_flag = False
                            pop_item = x
                            break
                    if add_x_flag:
                        x_split.add(item[0])
                    else:
                        x_split.remove(pop_item)
                        x_split.add(max(item[0], pop_item))
                        
        else:         
            for item in page.vertical_edges:
                if y_range and (y_range[-1]>item['y0'] or item['y0']>y_range[0]):
                    continue
                if y_range and (y_range[-1]>item['y1'] or item['y1']>y_range[0]):
                    continue
                if not x_split:
                    x_split.add(item['x0'])
                    if abs(item['x1']-item['x0'])>self.CURVES_MIN_MARGIN:
                        x_split.add(item['x1'])
                
                add_x0_flag = True
                add_x1_flag = True
                pop_x0_item = None
                pop_x1_item = None
                for x in x_split:
                    if abs(x-item['x0'])<self.CURVES_MIN_MARGIN:
                        add_x0_flag = False
                        pop_x0_item=x
                    if abs(x-item['x1'])<self.CURVES_MIN_MARGIN:
                        add_x1_flag = False
                        pop_x1_item=x
    
                if add_x0_flag:
                    x_split.add(item['x0'])
                else:
                    x_split.remove(pop_x0_item)
                    x_split.add(max(item['x0'], pop_x0_item))
                if add_x1_flag:
                    x_split.add(item['x1'])
                else:
                    if pop_x1_item in x_split:
                        x_split.remove(pop_x1_item)
                        x_split.add(max(item['x1'], pop_x1_item))

        return x_split

    def get_table_boundary(self, y_split, max_space_height=None):
        """
        一个页面可能有多个表格，根据纵坐标判断分了几个表格
        """
        if not max_space_height:
            max_space_height = self.MAX_SPACE_HEIGHT
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

    def fill_content_into_cell(self, xs, ys, words_list):
        """
        将解析的表格单元内容填入到对应的pd中，同时抽取该表对应的单位。

        Args:
            xs (list): 表格垂直线的x坐标
            ys (list): 表格水平线的y坐标
            words_list (list): 包含词坐标及文本的序列

        Returns:
            [type]: [description]
        """
        unit_feat = None
        ret_unit = 1
        words_id = -1
        data = [[None for i in range(len(xs)-1)] for j in range(len(ys)-1)]
        for words in words_list:
            words_id += 1
            x_begin = -1
            x_end = -1
            y_begin = -1
            y_end = -1
            x0 = words['x0']
            x1 = words['x1']
            top = words['top']
            bottom = words['bottom']
            if bottom<ys[-1]:
                continue
            if top<ys[0]+self.CELL_HEIGHT:
                unit_feat, unit = self.unit_rec.extract_unit(words['text'])
            for i in range(len(xs)):
                if x0>xs[i]:
                    x_begin = i
                if x1>xs[i]:
                    x_end = i+1
            
            for j in range(len(ys)):
                if top<ys[j]:
                    y_begin = j
                if bottom<ys[j]:
                    y_end = j+1
            if -1 in (x_begin, x_end, y_begin, y_end):
                continue
            if unit_feat:
                ret_unit = unit
            for i in range(y_begin, min(y_end, len(ys)-1)):
                for j in range(x_begin, min(x_end, len(xs)-1)):
                    data[i][j] = words['text']

        if all([not any(line) for line in data]):
            return None, None
            
        return pd.DataFrame(data), ret_unit

    def get_table_by_page(self, page, words_list=None):
        """根据page对象获取表格。
        由于pdfplumber对部分年报（例如招商银行2020半年报）的文字无法抽取，需要借助pymupdf。因此如果传入的
        words_list为空，则说明是来自于pdfplumber，如果不为空，则说明来自与pymupdf

        Returns:
            list: 返回的是一个list，里面的每个元素是一个字典:
                    "data": 抽取的表格
                    "unit": 该表格对应的单位
                    "page": 该表所在页
        """
        ret_list = []
        if not words_list:
            words_list = self.get_page_words(page)
        y_split = self.get_table_y(page)
        upbound, bottombound = get_bound_by_flag(words_list)
        table_boundary = get_table_boundary(y_split, upbound, bottombound)

        for table_id in table_boundary:
            memory = {}
            temp = table_boundary.get(table_id)
            for i in range(len(temp)-1):
                if float(temp[i])-float(temp[i+1])>self.MORE_THAN_ONE_CELL_HEIGHT:
                    memory[i] = find_proper_rows(temp[i], temp[i+1], words_list)
                    
            memory = sorted(memory.items(), key=lambda x:x[0], reverse=True)
            while memory:
                i,item = memory.pop(0)

                temp = temp[:i+1]+item+temp[i+1:]
            table_boundary[table_id] = temp

        for table_id in table_boundary:
            boundary = table_boundary[table_id]
            x_range = self.get_table_x(page, boundary)
            ys = boundary
            xs = sorted(x_range)
            # ys = [ys[0]+self.CELL_HEIGHT]+ys
            ys[-1] = ys[-1]-2
            cell_dict, unit = self.fill_content_into_cell(xs, ys, words_list)
            
            if cell_dict is not None and len(cell_dict)>2:
                ret_list.append({'data': cell_dict, 'unit': unit})
        
        return ret_list

    def get_words_from_pymupdf(self, page, max_adjacent_dis=None):
        """从pymupdf获取字符信息

        Args:
            max_adjacent_dis (int, optional): 如果在同一行的两个字符串首尾相邻不超过此值，则认为这两个字符串应该合并. Defaults to None.

        return:
            返回字符串信息，格式与pdfplumber类似
        """
        if not max_adjacent_dis:
            max_adjacent_dis = self.MAX_ADJACENT_DIS
        words = page.getTextWords()
        words_list = []
        for word in words:
            x0, top, x1, bottom, text, _, _, _ = word
            if words_list:
                temp = words_list[-1]
    #             print(word)
                if x0-temp['x1']<max_adjacent_dis and abs(top-temp['top']+3)<max_adjacent_dis:  #应该是连续字符串
                    temp['text'] = temp['text']+text
                    temp['x1'] = x1
                    continue

            temp = {'text': text, 'x0': x0, 'x1': x1, 'top': top+3, 'bottom': bottom}
            words_list.append(temp)
                
        return words_list

class ExtractTableWithLessLine:
    """抽取只有上下少数边界的表格
    """
    def __init__(self):
        self.MIN_TABLE_HEIGHT = 30

    def valid(self, xs, ys):
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
        """根据水平边界线，找到上下界

        Args:
            horizontal_edges (dict): 水平线，包含起始点的xy坐标

        Returns:
            Float: 上下边界
        """
        he_dict = {}
        ve_dict = {}
        for he in horizontal_edges:
            x0, x1, y0, y1 = he['x0'], he['x1'], he['y0'], he['y1']
            
            if y0 in ve_dict:
                temp = ve_dict.get(y0)
                temp.append(x0)
                ve_dict[y0] = temp
            else:
                exist = False
                for y in ve_dict:
                    if abs(y-y0)<1:
                        temp = ve_dict.get(y)
                        temp.append(x0)
                        ve_dict[y] = temp
                        exist = True
                        break
                if not exist:
                    ve_dict[y0] = [x0]
                    
            if x0 in he_dict:
                temp = he_dict.get(x0)
                temp.append(y0)
                he_dict[x0] = temp
            else:
                exist = False
                for x in he_dict:
                    if abs(x-x0)<1:
                        temp = he_dict.get(x)
                        temp.append(y0)
                        he_dict[x] = temp
                        exist = True
                        break
                if not exist:
                    he_dict[x0] = [y0]
                    
        xs = sorted(ve_dict.items(), key=lambda x:len(x[1]), reverse=True)
        ys = sorted(he_dict.items(), key=lambda x:len(x[1]), reverse=True)
        flag = self.valid(xs, ys)
        if flag != -1:
            x, ys = ys[flag][0], ys[flag][1]
        else:
            x, ys = ys[0][0], ys[0][1]
        ys = sorted(ys, reverse=True)
        if len(ys)>1:
            return x, ys[0], ys[-1]
        return None, None, None

    def get_words_line(self, word_list, height, up, down):
        """根据给定的上下边界，找到可能的表格范围内的数据

        Args:
            word_list (dict): page内的所有文本片段
            height (Float): page高度，用于计算y=height-top
            up (Float): 表格上边界
            dowun (Float): 表格下边界

        Returns:
            dict: key是行高（y）,value是[字符串，开始x坐标，终止x坐标]
        """
        words_line = {}
        for words in word_list:
            y = height-words['top']
            bottom = height-words['bottom']
            if bottom-up>3 or y<down:
                continue
            else:
                if y in words_line:
                    temp = words_line[y]
                    temp.append([words['text'], words['x0'], words['x1']])
                    words_line[y] = temp
                else:
                    exist = False
                    for y_ in words_line:
                        if abs(y-y_)<3:
                            temp = words_line[y_]
                            temp.append([words['text'], words['x0'], words['x1']])
                            words_line[y_] = temp
                            exist = True
                    if not exist:
                        words_line[y] = [[words['text'], words['x0'], words['x1']]]
        
        return words_line

    def judge(self, columns, x1, x2):
        """给定一个初始的列边界范围columns，然后根据给定的x1,x2不断修正边界

        Args:
            columns (list): 记录列边界的list，每一个元素又是一个list:[xl, xr]
            x1 (Float): 待确认的左边界
            x2 (Float): 待确认的右边界

        Returns:
            两种情况：
                1.当是合并单元格的情况时，返回合并的列号
                2.当是修正列边界的情况时，返回列号，和对应的新边界
        """
        assert x1<x2
        for i in range(len(columns)):
            x1_, x2_ = columns[i]
            if x1_<=x1<=x2_:
                if x1_<x2<x2_: #如果都在框架内，无贡献
                    return i, x1_, x2_
                else:
                    if i == len(columns)-1:#最后一列
                        return i, x1_, x2
                    elif columns[i+1][0]>x2: #扩大本列范围，而不是合并单元格
                        return i, x1_, x2
                    else:
                        j = i+1
                        while(j<len(columns)):
                            if columns[j][0]>x2:
                                return i, j-1, None
                            j += 1
                        return i, j-1, None
            elif x1_<=x2<=x2_:
                if i == 0: #第一列
                    return i, x1, x2_
                else:
                    j = i-1
                    while j>0:
                        if columns[j][1]<x1:
                            return i, j+1, None
                        j -= 1                        
                    return i, j+1, None
                
            elif x1<=x1_<=x2 and x1<=x2_<=x2: #覆盖框架
                if i == len(columns)-1: #最后一列
                    return i, x1, x2
                
                else:
                    j = i+1
                    while(j<len(columns)):
                            if columns[j][0]>x2:
                                if i==j-1:
                                    return i, x1, x2
                                return i, j-1, None
                            j += 1
                    
                    return i, j-1, None
        return None, None, None
        
    def split_cells(self, words_line):
        """通过调用judge方法不断修正列边界，从而得到最终的边界list。
        先判断该表最大宽度，构建一个全0边界框架，然后逐行获取字符串的首尾x坐标，来修正所在列的边界

        Args:
            words_line (dict): 存储每行字符串的字典

        Returns:
            修正之后的列边界列表，需要合并单元格的字符串
        """
        sorted_words_line = sorted(words_line.items(), key=lambda x:len(x[1]), reverse=True)
        column_num = len(sorted_words_line[0][1])
        column_side = [[0, 0] for i in range(column_num)]

        for i in range(len(sorted_words_line)):
            line = sorted_words_line[i]
            if len(line[1]) != column_num:
                break
            else:
                for j in range(column_num):
                    if column_side[j] == [0, 0]:
                        column_side[j] = [line[1][j][1], line[1][j][2]]
                    else:
                        if column_side[j][0]>line[1][j][1]:
                            column_side[j][0]=line[1][j][1]
                        if column_side[j][1]<line[1][j][2]:
                            column_side[j][1]=line[1][j][2]
        
        column_num -= 1
        merge_cols = []
        while column_num>0:
            for i in range(len(sorted_words_line)):
                line = sorted_words_line[i]
                if column_num != len(line[1]):
                    break
                for col in line[1]:
                    x1 = col[1]
                    x2 = col[2]

                    col_id, ls, rs = self.judge(column_side, x1, x2)
                    if rs is not None:
                        column_side[col_id] = [ls, rs]
                    else:
                        merge_cols.append([i, col_id, ls, line[1][0]])
            column_num -= 1
            
        return column_side, merge_cols

    def get_no_line_table(self, column_side, words_line):
        """
        提取只有上下边界的表格
        """
        words_line = sorted(words_line.items(), key=lambda x:x[0], reverse=True)
        data = [[None for i in range(len(column_side))] for j in range(len(words_line))]
        for i in range(len(words_line)):
            for word in words_line[i][1]:
                for j in range(len(column_side)):
                    if column_side[j][0]<=word[1]<=column_side[j][1]:
                        data[i][j] = word[0]
                    if column_side[j][0]<=word[2]<=column_side[j][1]:
                        data[i][j] = word[0]
        return pd.DataFrame(data)

    def get_table(self, page, word_list=None, column_side=None, table_name=''):
        """
        接口，返回表格
        """
        try:
            if not word_list:
                word_list = page.extract_words()
            _, up, dowun = self.find_first_last_line(page.horizontal_edges)
            if abs(up-dowun)<self.MIN_TABLE_HEIGHT:
                return None, None
            words_line = self.get_words_line(word_list, page.height, up, dowun)
            if not column_side:
                column_side, merge_cols = self.split_cells(words_line)
            # if table_name:
            #     for words in word_list:
            #         text = words['text']
            #         top = page.height-words['top']
                    
            return column_side, self.get_no_line_table(column_side, words_line)
        except:
            return None, None
        
