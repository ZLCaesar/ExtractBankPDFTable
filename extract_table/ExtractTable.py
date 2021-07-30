from package.toolkit import UnitRec

class ExtractTable(object):
    def __init__(self):
        self.MAX_ADJACENT_DIS = 5
        self.unit_rec = UnitRec()

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
            
        #删除全None行
        for i, row in table.iterrows():
            if (row.isnull().all()):
                table = table.drop(i)
        table = table.reset_index(drop=True)
        return table

    def get_words_from_pymupdf(self, page, max_adjacent_dis):
        """从pymupdf获取字符信息

        Args:
            max_adjacent_dis (int, optional): 如果在同一行的两个字符串首尾相邻不超过此值，则认为这两个字符串应该合并

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

            temp = {'text': text, 'x0': x0+1, 'x1': x1-1, 'top': top+3, 'bottom': bottom}
            words_list.append(temp)
                
        return words_list

    def get_page_words(self, page, fitz_page=None, max_adjacent_dis=None):
        """
        转换每个字符的y坐标，使其与线坐标一致。（字符的y坐标其实位置在顶部，而线坐标的起始位置在底部）
        """
        if fitz_page:
            words_list = self.get_words_from_pymupdf(fitz_page, max_adjacent_dis)
        else:
            words_list = page.extract_words()

        for i in range(len(words_list)):
            words_list[i]['top'] = float(page.height)- float(words_list[i]['top'])
            words_list[i]['bottom'] = float(page.height) - float(words_list[i]['bottom'])
            words_list[i]['x0'] = words_list[i]['x0'] + 1
            words_list[i]['x1'] = words_list[i]['x1'] - 1
        words_list = sorted(words_list, key=lambda x:x['top'], reverse=True)
        
        return words_list
        
    def get_table_by_page(self):
        raise NotImplementedError
