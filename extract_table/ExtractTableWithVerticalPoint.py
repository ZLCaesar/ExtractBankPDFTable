import numpy as np
import pandas as pd

from .ExtractTable import ExtractTable
from package.deal_row_boundry import get_bound_by_flag, get_table_boundary, find_proper_rows

class ExtractTableWithVerticalPoint(ExtractTable):
    def __init__(
        self, 
        CURVES_MIN_MARGIN=8, 
        MAX_SPACE_HEIGHT=40, 
        CELL_HEIGHT=25, 
        MORE_THAN_ONE_CELL_HEIGHT=28
        ):
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
        super(ExtractTableWithVerticalPoint, self).__init__()
        self.CURVES_MIN_MARGIN = CURVES_MIN_MARGIN
        self.MAX_SPACE_HEIGHT = MAX_SPACE_HEIGHT
        self.CELL_HEIGHT = CELL_HEIGHT
        self.MORE_THAN_ONE_CELL_HEIGHT = MORE_THAN_ONE_CELL_HEIGHT
        

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
        table_list = []
        if not words_list:
            words_list = self.get_page_words(page)
        y_split = self.get_table_y(page)
        upbound, bottombound = get_bound_by_flag(words_list)
        table_boundary = get_table_boundary(y_split, upbound, bottombound)

        for table_id in table_boundary:
            memory = {}
            temp = table_boundary.get(table_id)
            for i in range(len(temp)-1):
                if float(temp[i])-float(temp[i+1])>self.MORE_THAN_ONE_CELL_HEIGHT:  #如果距离超过阈值，则认为可能存在多行，进入findproperrows函数进行拆分
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
                table_list.append({'data': cell_dict, 'unit': unit})

        return table_list