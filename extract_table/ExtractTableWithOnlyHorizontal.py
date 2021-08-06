from re import U
import pandas as pd

from .BaseExtractTable import BaseExtractTable
from .DealRowBound import DealBoundary

class ExtractTableWithOnlyHorizontal(BaseExtractTable):
    """抽取只有上下少数边界的表格
    """
    def __init__(self,
        CURVES_MIN_MARGIN = 8,
        MAX_ADJACENT_DIS = 5,
        UNDER_THIS = [],
        START_FROM_THIS = [],
        ABOVE_THIS = [],
        BOUND_FLAG_DIS_TOLERANCE = 2):
        super(ExtractTableWithOnlyHorizontal, self).__init__(CURVES_MIN_MARGIN, MAX_ADJACENT_DIS)
        self.MIN_TABLE_HEIGHT = 30
        self.deal_bound = DealBoundary(UNDER_THIS, START_FROM_THIS, ABOVE_THIS, BOUND_FLAG_DIS_TOLERANCE)

    def get_words_line(self, word_list, up, down):
        """根据给定的上下边界，找到可能的表格范围内的数据

        Args:
            word_list (dict): page内的所有文本片段
            up (Float): 表格上边界
            dowun (Float): 表格下边界

        Returns:
            dict: key是行高（y）,value是[字符串，开始x坐标，终止x坐标]
        """
        words_line = {}
        unit_feat = None 
        unit = 1
        for words in word_list:
            y = words['top']
            bottom = words['bottom']
            if not unit_feat:
                unit_feat, unit = self.unit_rec.extract_unit(words['text'])
            
            if bottom-up>3 or y<down:
                continue
            else:
                if bottom in words_line:
                    temp = words_line[bottom]
                    temp.append([words['text'], words['x0'], words['x1']])
                    words_line[bottom] = temp
                else:
                    exist = False
                    for bottom_ in words_line:
                        if abs(bottom-bottom_)<5:
                            temp = words_line[bottom_]
                            temp.append([words['text'], words['x0'], words['x1']])
                            words_line[bottom_] = temp
                            exist = True
                    if not exist:
                        words_line[bottom] = [[words['text'], words['x0'], words['x1']]]
        
        return words_line, unit

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

        temp_words = []
        for i in range(len(sorted_words_line)):
            line = sorted_words_line[i]
            if len(line[1]) != column_num:
                temp_words+=line[1]
            else:
                for j in range(column_num):
                    if column_side[j] == [0, 0]:
                        column_side[j] = [line[1][j][1], line[1][j][2]]
                    else:
                        if column_side[j][0]>line[1][j][1]:
                            column_side[j][0]=line[1][j][1]
                        if column_side[j][1]<line[1][j][2]:
                            column_side[j][1]=line[1][j][2]

        while temp_words:
            words = temp_words.pop(0)
            left_scan = False
            right_scan = False
            words_left = words[1]
            words_right = words[2]
            col_left = column_side[0][0]
            if words_left<col_left:
                column_side[0][0] = words_left

            for i in range(1, len(column_side)):
                col_left = column_side[i][0]
                col_right = column_side[i][1]
                if col_left>words_right:
                    column_side[i-1][1] = max(column_side[i-1][1], words_right)
                if col_left>words_left>column_side[i-1][1]:
                    column_side[i][0] = words_left

                # right = column_side[i][1]
               
                # if words[1]>right:
                #     right_scan = True
                #     column_side[i][1] = words[2]

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
        print(column_side)
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
                    if column_side[j][0]<=word[1]<=column_side[j][1]: #字的左边界在单元格内，则填入该单元格
                        data[i][j] = word[0]
                    if column_side[j][0]<=word[2]<=column_side[j][1]: #字的右边界在单元格内，则填入该单元格
                        data[i][j] = word[0]
                    
        return pd.DataFrame(data)


    # def get_table_by_page(self, page, word_list=None, column_side=None):
    #     """
    #     接口，返回表格
    #     """
    #     try:
    #         if not word_list:
    #             word_list = page.extract_words()
    #         _, up, dowun = self.find_first_last_line(page.horizontal_edges)
    #         if abs(up-dowun)<self.MIN_TABLE_HEIGHT:
    #             return None, None
    #         words_line = self.get_words_line(word_list, page.height, up, dowun)
    #         if not column_side:
    #             column_side, merge_cols = self.split_cells(words_line)
    #         return column_side, self.get_no_line_table(column_side, words_line)
    #     except:
    #         return None, None
        
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
        table_list = []
        top_line_y = 0
        bottom_line_y = 100000
        if not words_list:
            words_list = self.get_page_words(page)
        y_split = self.get_table_y(page)
        upbound, bottombound = self.deal_bound.get_bound_by_flag(words_list)
        table_boundary = self.deal_bound.get_table_boundary(y_split, upbound, bottombound)

        for table_id in table_boundary:
            boundary = table_boundary[table_id]
            up, down = float(boundary[0]), float(boundary[-1])
            top_line_y = max(top_line_y, up)
            bottom_line_y = min(bottom_line_y, down)
            if abs(up-down)<self.MIN_TABLE_HEIGHT:
                continue
            words_line, unit = self.get_words_line(words_list, up, down)
            column_side, merge_cols = self.split_cells(words_line)
            table = self.get_no_line_table(column_side, words_line)
            table_list.append({'data': table, 'unit': unit, 'top': up, 'bottom': down})
        return table_list, top_line_y, bottom_line_y
        # return table_list