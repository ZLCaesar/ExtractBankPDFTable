import pandas as pd

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
            ve_dict = iter_dict(y, x, ve_dict)
            he_dict = iter_dict(x, y, he_dict)
            
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
            return column_side, self.get_no_line_table(column_side, words_line)
        except:
            return None, None
        
