from re import U
import numpy as np
import pandas as pd

from .BaseExtractTable import BaseExtractTable
from .DealRowBound import DealBoundary

class ExtractTableWithVerticalPoint(BaseExtractTable):
    def __init__(
        self, 
        CURVES_MIN_MARGIN=8,
        CELL_MIN_MARGIN=8,
        MAX_ADJACENT_DIS=5, 
        MAX_SPACE_HEIGHT=40, 
        CELL_HEIGHT=25, 
        MORE_THAN_ONE_CELL_HEIGHT=28,
        UP_DEVIATION_TOLERANCE=0,
        DOWN_DEVIATION_TOLERANCE=0,
        UNDER_THIS = [],
        START_FROM_THIS = [],
        ABOVE_THIS = [],
        BOUND_FLAG_DIS_TOLERANCE = 2,
        MULTI_CELL_TOLERANCE_RATE = 0.1
        ):
        """抽取表格，适用的表格形式：
                1. 横竖线充足（约等于完美表格）
                2. 视觉上只有水平线，但有列分割结点（视觉上没有垂直线，但水平线按照列进行了分段）

        Args:
            CURVES_MIN_MARGIN (int, optional): 一个cell的上下距离如果没有超过此值，则不认为其是一条有效边界. Defaults to 8.
            MAX_SPACE_HEIGHT (int, optional): 用于确定表之间的边界，当边界大于此值时，认为不是同一张表. Defaults to 40.
            CELL_HEIGHT (int, optional): 一个表格CELL的高度. Defaults to 25.
            MORE_THAN_ONE_CELL_HEIGHT (int, optional): 如果两条水平线的高度差超过此值，则认为有合并单元格的存在. Defaults to 28.
            UP_DEVIATION_TOLERANCE (int, optional): 上偏差容忍度，即在表格中，如果value的顶边线有重叠，重叠程度小于此值则认为在这个cell中. Defaults to 0.
            DOWN_DEVIATION_TOLERANCE (int, optional): 下偏差容忍度，即在表格中，如果value的底边线有重叠，重叠程度小于此值则认为在这个cell中. Defaults to 0.
            MULTI_CELL_TOLERANCE_RATE: 当出现一个字符串在多个表格的情况时，如果超出比例小于此值，则不进行填充
        """
        super(ExtractTableWithVerticalPoint, self).__init__(CURVES_MIN_MARGIN, MAX_ADJACENT_DIS, CELL_MIN_MARGIN)
        self.MAX_SPACE_HEIGHT = MAX_SPACE_HEIGHT
        self.CELL_HEIGHT = CELL_HEIGHT
        self.MORE_THAN_ONE_CELL_HEIGHT = MORE_THAN_ONE_CELL_HEIGHT
        self.UP_DEVIATION_TOLERANCE = UP_DEVIATION_TOLERANCE
        self.DOWN_DEVIATION_TOLERANCE = DOWN_DEVIATION_TOLERANCE
        self.MULTI_CELL_TOLERANCE_RATE = MULTI_CELL_TOLERANCE_RATE
        self.deal_bound = DealBoundary(UNDER_THIS, START_FROM_THIS, ABOVE_THIS, BOUND_FLAG_DIS_TOLERANCE)

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
                # print(unit_feat, unit)
            for i in range(len(xs)):
                if x0>xs[i]:
                    x_begin = i
                if x1>xs[i]:
                    x_end = i+1
            if x_end - x_begin > 1 and x_begin+1<len(xs):
                cell_lenth = float(xs[x_begin+1]-xs[x_begin])
                dis = float(xs[x_begin+1])-float(x0)
                if dis/cell_lenth<self.MULTI_CELL_TOLERANCE_RATE:
                    x_begin += 1

            for j in range(len(ys)):
                if top<float(ys[j])+self.UP_DEVIATION_TOLERANCE:
                    y_begin = j
                if bottom<float(ys[j])-self.DOWN_DEVIATION_TOLERANCE:
                    y_end = j+1
            
            if unit_feat is not None:
                ret_unit = unit
            if -1 in (x_begin, x_end, y_begin, y_end):
                continue
            for i in range(y_begin, min(y_end, len(ys)-1)):
                for j in range(x_begin, min(x_end, len(xs)-1)):
                    # if data[i][j] and data[i][j]!=words['text']:
                    #     data[i][j] += words['text']
                    # else:
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
        top_line_y = 0
        bottom_line_y = 100000

        if not words_list:
            words_list = self.get_page_words(page)
        y_split = self.get_table_y(page)
        upbound, bottombound = self.deal_bound.get_bound_by_flag(words_list)
        table_boundary = self.deal_bound.get_table_boundary(y_split, upbound, bottombound)

        for table_id in table_boundary:
            memory = {}
            temp = table_boundary.get(table_id)
            for i in range(len(temp)-1):
                if float(temp[i])-float(temp[i+1])>self.MORE_THAN_ONE_CELL_HEIGHT:  #如果距离超过阈值，则认为可能存在多行，进入findproperrows函数进行拆分
                    memory[i] = self.deal_bound.find_proper_rows(temp[i], temp[i+1], words_list)
                    
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
            top_line_y = max(top_line_y, ys[0])
            bottom_line_y = min(bottom_line_y, ys[-1])
            if cell_dict is not None and len(cell_dict)>=1:
                table_list.append({'data': cell_dict, 'unit': unit, 'top': ys[0], 'bottom': ys[-1]})

        return table_list, top_line_y, bottom_line_y