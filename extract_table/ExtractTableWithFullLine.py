import re
import pandas as pd

from .BaseExtractTable import BaseExtractTable

class ExtractTableWithFullLine(BaseExtractTable):
    def __init__(self, args):
        super(ExtractTableWithFullLine, self).__init__(args)
        self.UNDER_THIS = args['under_this']
        
    def get_table_by_page(self, page, words_list):
        table_list = []
        tables = page.extract_tables()
        top_line = -1
        bottom_line = 10000
        if tables:
            for table in tables:
                table = pd.DataFrame(table)
                table, unit, table_top, table_bottom = self.clean_table(table, words_list)
                table_list.append({'data': table, 'unit': unit, 'top': table_top, 'bottom': table_bottom})
                top_line = max(top_line, table_top)
                bottom_line = min(bottom_line, table_bottom)
        return table_list, top_line, bottom_line

    def __detect_dict(self, row_dict):
        for key in row_dict:
            if row_dict[key]['top'] == -1:
                return False

        return True

    def clean_table(self, table, words_list):
        first_row = {}
        last_row = {}
        for i, row in table.iterrows():
            for j in range(len(row)):
                if i == 0:
                    if row[j] is not None:
                        first_row[row[j].split('\n')[0]] = {'top': -1, 'bottom': 10000}
                if i == len(table)-1:
                    if row[j] is not None:
                        last_row[row[j].split('\n')[0]] = {'top': -1, 'bottom': 10000}
                if table.iloc[i,j] is not None:
                    table.iloc[i,j] = table.iloc[i,j].replace('\n','')

        unit_line = []
        unit = 1
        for i in range(len(words_list)):
            text = words_list[i]['text']
            top = words_list[i]['top']
            bottom = words_list[i]['bottom']
            for pattern in self.UNDER_THIS:
                if re.findall(pattern, text):
                    # print(pattern, text)
                    unit_line.append([text, bottom])

            if text in first_row:
                first_row[text]['top'] = top
                first_row[text]['bottom'] = bottom
            elif text in last_row:
                last_row[text]['top'] = top
                last_row[text]['bottom'] = bottom

            if self.__detect_dict(last_row):
                break
        
        table_top = -1
        table_bottom = 10000
        for _, value in first_row.items():
            table_top = max(table_top, value['top'])
        for _, value in last_row.items():
            table_bottom = min(table_bottom, value['bottom'])

        for text, position in unit_line:
            if position>table_top and position-table_top<15:
                _, unit = self.unit_rec.extract_unit(text)
                break
       

        return table, unit, table_top, table_bottom