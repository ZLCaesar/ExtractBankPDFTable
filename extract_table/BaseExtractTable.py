import re
from zhconv import convert
from package.toolkit import UnitRec

class BaseExtractTable(object):
    def __init__(self, args):
        """[summary]

        Args:
            MAX_ADJACENT_DIS (int, optional): 在使用pymupdf解析pdf抽取文字时，有些视觉上相邻的字符串是抽取出来是断开的，如果两个在同一行上的字符
            串的首尾距离小于此值，则认为两者应该相连. Defaults to 5.
        """
        self.CELL_MIN_MARGIN = args['cell_min_margin']
        self.MAX_ADJACENT_DIS = args['max_adjacent_dis']
        self.CURVES_MIN_MARGIN = args['curves_min_margin']
        self.unit_rec = UnitRec(args['unit_patterns'])
        self.args = args

    def drop_duplicate_cols(self, table):
        """对抽取出来的表进行后处理。由于坐标细微误差，有可能导致:
            1. 多出来一列全None
            2. 或者相同的两列
            3. 多出来一行全None
        需要对其进行删除。
        方法为：
            1. 相邻两列进行比较，如果后一列每行元素要么是None，要么与前一列相同，则该列为冗余列，删除。
            2. 遍历每一行，drop全None行
        """
        def detect(curr_col, next_col):
            temp = []
            for j in range(len(next_col)):
                if next_col[j] is None:
                    temp.append(True)
                elif next_col[j] == curr_col[j]:
                    temp.append(True)
                else:
                    temp.append(False)
            if all(temp):
                return True
            return False
        if len(table) == 1:
            return table
        i = 0
        while i < len(table.columns)-1:
            curr_col = list(table[i])
            next_col = list(table[i+1])
            if detect(curr_col, next_col):
                table = table.drop(i+1, axis=1)
                table.columns = list(range(len(table.columns)))
                i = 0
            elif detect(next_col, curr_col):
                table = table.drop(i, axis=1)
                table.columns = list(range(len(table.columns)))
                i = 0
            else:
                i += 1

        i = 0
        while i < len(table)-1:
            curr_row = list(table.iloc[i])
            next_row = list(table.iloc[i+1])
            if detect(curr_row, next_row):
                table = table.drop(i+1)
                i = 0
                table = table.reset_index(drop=True)
            elif detect(next_row, curr_row):
                table = table.drop(i)
                i = 0
                table = table.reset_index(drop=True)
            else:
                i += 1
            
        #删除全None行
        # for i, row in table.iterrows():
        #     if (row.isnull().all()):
        #         table = table.drop(i)
        # table = table.reset_index(drop=True)
        return table

   
    def get_words_from_pymupdf(self, page):
        """从pymupdf获取字符信息

        Args:
            max_adjacent_dis (int, optional): 如果在同一行的两个字符串首尾相邻不超过此值，则认为这两个字符串应该合并

        return:
            返回字符串信息，格式与pdfplumber类似
        """
        words = page.getTextWords()
        words_list = []
        for word in words:
            x0, top, x1, bottom, text, _, _, _ = word
            if words_list:
                temp = words_list[-1]
    #             print(word)
                if x0-temp['x1']<self.MAX_ADJACENT_DIS and abs(top-temp['top']+3)<self.MAX_ADJACENT_DIS:  #应该是连续字符串
                    temp['text'] = temp['text']+text
                    temp['x1'] = x1
                    continue

            temp = {'text': text.replace(' ',''), 'x0': x0+1, 'x1': x1-1, 'top': top+3, 'bottom': bottom}
            words_list.append(temp)
                
        return words_list

    def get_page_words(self, page, fitz_page=None):
        """
        转换每个字符的y坐标，使其与线坐标一致。（字符的y坐标其实位置在顶部，而线坐标的起始位置在底部）
        """
        def _is_neibor(word, temp, dev=0):
            if abs(word['x0']-temp['x1'])<self.MAX_ADJACENT_DIS+dev and abs(word['top']-temp['top']+1)<self.MAX_ADJACENT_DIS:
                return True
            return False

        if fitz_page:
            words_list = self.get_words_from_pymupdf(fitz_page)
        else:
            words = page.extract_words()
            words_list = []
            for word in words:
                if words_list:
                    temp = words_list[-1]
        #             print(word)
                    if _is_neibor(word, temp) and re.findall(r'\d{4}年\d{1,2}-\d{1,2}月', temp['text']):
                        pass
                    elif _is_neibor(word, temp):  #应该是连续字符串
                        temp['text'] = temp['text']+word['text']
                        temp['x1'] = word['x1']
                        continue
                    elif _is_neibor(word, temp, 2) and temp['text'] == '-':
                        temp['text'] = temp['text']+word['text']
                        temp['x1'] = word['x1']
                        continue
                    
                temp = {'text': word['text'].replace(" ",""), 'x0': word['x0'], 'x1': word['x1'], 'top': word['top'], 'bottom': word['bottom']}
                words_list.append(temp)

        for i in range(len(words_list)):
            words_list[i]['top'] = float(page.height)- float(words_list[i]['top'])
            words_list[i]['bottom'] = float(page.height) - float(words_list[i]['bottom'])
            words_list[i]['x0'] = float(words_list[i]['x0'] + 1)
            words_list[i]['x1'] = float(words_list[i]['x1'] - 1)
            

            if self.args.get('zhcn_convert', False):
                words_list[i]['text'] = convert(words_list[i]['text'], 'zh-cn')
        words_list = sorted(words_list, key=lambda x:x['top'], reverse=True)
        if self.args.get('drop_first_word', False) and words_list:
            words_list.pop(0)
        if self.args.get('drop_last_word', False) and words_list:
            for _ in range(self.args.get('drop_last_word')):
                if not words_list:
                    break
                words_list.pop(-1)
        return words_list
    
    def get_table_y(self, page):
        """
        获取每一行所在的纵坐标
        """
        y_split = set()
        if self.args['curves_first'] and page.curves:
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

        return sorted(y_split, reverse=True)

    def get_table_x(self, page, y_range=[]):
        """
        获取每一列的横坐标
        """
        x_split = set()
        standar_line = page.vertical_edges if self.args['curves_first'] else page.horizontal_edges
        if self.args['curves_first'] and page.curves:
            for i in range(len(page.curves)):
                for item in page.curves[i]['pts']:
                    if y_range and (y_range[-1]>item[1] or item[1]>y_range[0]):
                        continue
                    if not x_split:
                        x_split.add(item[0])
                    add_x_flag = True
                    pop_item = None
                    for x in x_split:
                        if abs(x-item[0])<self.CELL_MIN_MARGIN:
                            add_x_flag = False
                            pop_item = x
                            break
                    if add_x_flag:
                        x_split.add(item[0])
                    else:
                        x_split.remove(pop_item)
                        x_split.add(max(item[0], pop_item))
                    
        else:
            for item in standar_line:
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
                    if abs(x-item['x0'])<self.CELL_MIN_MARGIN:
                        add_x0_flag = False
                        pop_x0_item=x
                    if abs(x-item['x1'])<self.CELL_MIN_MARGIN:
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

    def get_table_by_page(self):
        raise NotImplementedError
