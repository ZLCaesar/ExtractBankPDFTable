import locale
from tqdm import tqdm
from .DetectMainTable import ThreeBTable
from .ExtractTable import ExtractTableWithLessLine
from .FindIndex import find_recent_year_column, get_index

class ExtractIndex:
    def __init__(self, max_line=5):
        self.ext_tab = ExtractTableWithLessLine()
        self.tbt = ThreeBTable(max_line)

    def extract_index(self, pages, table_name="利润表", year='2020', has_group=False):
        tables = []
        for i in tqdm(range(len(pages))):
            if i == 27:
                print(i)
            page = pages[i]
            word_list = page.extract_words()
            table_type, unit_name, unit_num = self.tbt.is_main_table(word_list, table_name)
            if table_type == 1:
                column_side, table = self.ext_tab.get_table(page)
            elif table_type == 2:
                column_side, table = self.ext_tab.get_table(page, column_side)
            else:
                column_side = None
                table = None
            if table is not None:
                range1, range2 = self.tbt.is_bank_table(table)
                if has_group:
                    if range1 + range2 != -2:
                        tables.append([table, range1, range2, unit_name, unit_num])
                else:
                    tables.append([table, range1, range2, unit_name, unit_num])
        info = []
        for i in range(len(tables)):
            table, range1, range2, unit_name, unit_num = tables[i]
            _, year_column = find_recent_year_column(table, year)
            if year_column == -1:
                continue
            result = get_index(table, year_column)
            info.append([result, unit_name, unit_num])

        return info

    def convert_num(self, num):
        try:
            num = num.replace('(','').replace(')','').replace('（','').replace('）','')
            locale.setlocale( locale.LC_ALL, 'en_US.UTF-8' )
            return locale.atof(num)
        except:
            return None

    def map2index(self, index_alias_dict, info):
        ret = []

        for index in info:
            index_pair, unit_name, unit_num = index
            for index_name, index in index_pair:
                if index_name in index_alias_dict:
                    index = self.convert_num(index)
                    if index is None:
                        continue
                    if unit_name:
                        ret.append((index_alias_dict.get(index_name), index*unit_num))
                    else:
                        ret.append((index_alias_dict.get(index_name), index))

        return ret

    def get_index(self, info):
        ret = []
        for index in info:
            index_pair, unit_name, unit_num = index
            for index_name, index in index_pair:
                index = self.convert_num(index)
                if index is None:
                    continue
                if unit_name:
                    ret.append((index_name, index*unit_num))
                else:
                    ret.append((index_name, index))

        return ret