class ThreeBTable:
    def __init__(self, max_line = 5) -> None:
        self.max_line = max_line
        self.continue_keywords = '续'
        self.bank_flag = "本行"
        self.group_flag = "本集团"
        self.unit_flag = "单位"
        self.units = {
            "千万元": 10000000,
            "百万元": 1000000,
            "十万元": 100000,
            "万元": 10000,
            "千亿元": 100000000000,
            "百亿元": 10000000000,
            "十亿元": 1000000000,
            "亿元": 100000000
        }

    def is_intersect(self, x, y):
        if y[0]<=x[0]<=y[1]:
            return True
        
        if x[0]<=y[0]<=x[1]:
            return True
        
        return False

    def assign_line_id(self, word_list):
        line_id_map = {}
        before_top, before_bottom = -1, -1
        line_id = 0
        for i in range(len(word_list)):
            string_info = word_list[i]
            top = string_info['top']
            bottom = string_info['bottom']
            if before_top == -1:
                line_id_map[i] = line_id
                before_top, before_bottom = top, bottom
            else:
                if self.is_intersect([before_top, before_bottom], [top, bottom]):
                    line_id_map[i] = line_id
                else:
                    line_id += 1
                    line_id_map[i] = line_id
                    before_top, before_bottom = top, bottom
                    
        return line_id_map

    def is_main_table(self, word_list, table_name):
        """根据关键字来判断是否是所需三大表。同时判断是否是续表。

        Args:
            word_list ([type]): [description]
            table_name (str): 表名关键字---资产负债表、利润表、现金流量表等

        Returns:
            int: 根据返回数字判断情况
            0: 不存在表
            1: 存在该表
            2: 存在该表且为续表
        """
        line_id_map = self.assign_line_id(word_list)
        for i in range(len(word_list)):
            word_info = word_list[i]
            text = word_info['text']
            unit_name, unit_num = None, -1
            if table_name in text:
                for j in range(i, len(word_list)):
                    if line_id_map.get(j) > self.max_line+2:
                        break
                    unit_name, unit_num = self.get_unit(word_list[j]['text'])
                    if unit_name:
                        break

                if self.continue_keywords in text:   #表中存在“续”
                    return 2, unit_name, unit_num
                return 1, unit_name, unit_num
            if line_id_map.get(i)>self.max_line:
                return 0, unit_name, unit_num
            
        return 0, None, -1

    def get_unit(self, words):
        if self.unit_flag in words:
            for item in self.units:
                if item in words:
                    return item, self.units[item]
        
        return None, -1

    def is_bank_table(self, table):
        begin, end = -1, -1
        for i, row in table.iterrows():
            if i>self.max_line:
                break
            for j in range(len(row)):
                if row[j] == self.bank_flag:
                    begin = j
                elif row[j] == self.group_flag:
                    end = j
        if begin == -1:      #说明表里没有本行
            return -1, -1
        elif begin < end:     #说明表里既有本行又有集团，且本行在集团之前
            return begin, end
        else:  
            return begin, -1

    