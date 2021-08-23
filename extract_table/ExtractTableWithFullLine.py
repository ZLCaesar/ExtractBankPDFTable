import re
import pandas as pd

from .BaseExtractTable import BaseExtractTable

class ExtractTableWithFullLine(BaseExtractTable):
    def __init__(self, args):
        super(ExtractTableWithFullLine, self).__init__(args)
        self.UNDER_THIS = args['under_this']
        self.MAX_SPACE_HEIGHT = args['max_space_height']
        self.FIND_HEAD_MORE = args['find_head_more']
        
    def get_table_by_page(self, page, words_list):
        table_list = []
        tables = page.extract_tables()
        top_line = -1
        bottom_line = 10000
        bottom_flag = 10000
        if tables:
            for table in tables:
                table = pd.DataFrame(table)
                table, unit, table_top, table_bottom = self.clean_table(table, words_list, bottom_flag)
                table_list.append({'data': table, 'unit': unit, 'top': table_top, 'bottom': table_bottom})
                top_line = max(top_line, table_top)
                bottom_line = min(bottom_line, table_bottom)
                table_list = sorted(table_list, key=lambda x:x['top'], reverse=True)
                bottom_flag = table_bottom
        return table_list, top_line, bottom_line

    def __detect_dict(self, first_row, last_row, bottom_flag):
        first_find = False
        up = -1
        bottom = 10000
        for key in first_row:
            if first_row[key]['top'] != -1:
                up = first_row[key]['top']
                break
        for key in last_row:
            if last_row[key]['top'] == -1:
                return False
            bottom = last_row[key]['top']
        if up != -1 and up > bottom and up < bottom_flag:
            return True
        return False

    def clean_table(self, table, words_list, bottom_flag):
        """1. 使用pdfplumber自带的表格抽取器时，有换行存在的表格中间会有\n，需要将其去掉。
        2. 同时根据表的第一行和最后一行，找到表格的上下边界的坐标。
        3. 抽取器抽取的多个表格顺序是随机的，需要根据各个表的top进行重新排序
        4. 某些表格上边界线消失，抽取器不能抽取第一行，需要进行补充，规则为，如果在现有表格的第一行的上面 
            有n个字符串，n=表格列的个数，则认为这个是表的真正的第一行，从而取而代之

        Args:
            table ([type]): [description]
            words_list ([type]): [description]

        Returns:
            [type]: [description]
        """
        first_row = {}
        last_row = {}
        for i, row in table.iterrows():
            for j in range(len(row)):
                if i == 0:
                    if row[j] is not None:
                        first_row[row[j].split('\n')[0].replace(" ", "")] = {'top': -1, 'bottom': 10000}
                if i == len(table)-1:
                    if row[j] is not None:
                        last_row[row[j].split('\n')[0].replace(" ", "")] = {'top': -1, 'bottom': 10000}
                if table.iloc[i,j] is not None:
                    table.iloc[i,j] = table.iloc[i,j].replace('\n','')

        # print(first_row)
        unit_line = []
        unit = 1
        head = []            #可能的表格真第一行
        flag_head = False    #找到真第一行的标记
        flag_first = False   #words_list遍历的时候，第一次进入了first_row的标记
        for i in range(len(words_list)):
            text = words_list[i]['text']
            top = words_list[i]['top']
            bottom = words_list[i]['bottom']
            if not flag_first:     #如果还没有进入到表格的第一行，那么前面的字符都有可能是潜在的第一行字符串
                head.append([text, top, bottom])
            for pattern in self.UNDER_THIS:
                if re.findall(pattern, text):
                    unit_line.append([text, bottom])

            if text in first_row:
                if not flag_first:     #如果第一次找到了first_row里面的字符串元素
                    flag_first = True  #将标记打开，以后就不再进入此代码
                    if len(head) == len(first_row)+self.FIND_HEAD_MORE: #如果head里的元素个数 等于表格列数+2（2为页眉等的信息+first_row的第一个元素）
                        flag_head = True  #将标记打开，说明找到了真第一行
                        head = head[self.FIND_HEAD_MORE-1:len(head)-1]
                
                first_row[text]['top'] = top
                first_row[text]['bottom'] = bottom
            if text in last_row:
                last_row[text]['top'] = top
                last_row[text]['bottom'] = bottom

            if self.__detect_dict(first_row, last_row, bottom_flag):
                break
        table_top = -1
        table_top2 = -2
        table_bottom = 10000
        for _, value in first_row.items():
            table_top = max(table_top, value['top'])
        if flag_head: #找到了真第一行之后，需要取代top同时将其拼接到原表之前。
            for item in head:
                table_top2 = max(table_top2, item[1])
            if table_top2 > table_top and table_top2-table_top<self.MAX_SPACE_HEIGHT:
                table_top = table_top2
                table = pd.DataFrame([[item[0] for item in head]]).append(table)
                table = table.reset_index(drop=True)
        for _, value in last_row.items():
            table_bottom = min(table_bottom, value['bottom'])

        for text, position in unit_line:
            if position>table_top and position-table_top<15:
                _, unit = self.unit_rec.extract_unit(text)
                break
       
        return table, unit, table_top, table_bottom