import re
import locale

class UnitRec:
    def __init__(self, patterns):
        self.units = {
            "千万元": 10000000,
            "百万元": 1000000,
            "十万元": 100000,
            "万元": 10000,
            "千元": 1000,
            "千亿元": 100000000000,
            "百亿元": 10000000000,
            "十亿元": 1000000000,
            "亿元": 100000000
        }
        self.patterns = patterns

    def extract_unit(self, word):
        for pattern in self.patterns:
            finds = re.findall(pattern, word)
            if finds:
                finds[0] = finds[0].replace(')', '').replace('）', '').replace(' ', '')
                if finds[0] in self.units:
                    return finds[0], self.units[finds[0]]

        return None, 1

    def convert_num(self, num):
        try:
            num = num.replace('(','').replace(')','').replace('（','').replace('）','')
            locale.setlocale( locale.LC_ALL, 'en_US.UTF-8' )
            return locale.atof(num)
        except:
            return None

    def covert_text_num(self, text):
        if not text:
            return None
        if "%" in text:
            return text.replace("%", "")
        for item in self.units:
            u = item.replace("元", "")
            if u in text:
                return self.convert_num(text.replace(u, ""))*self.units[item]
        return None