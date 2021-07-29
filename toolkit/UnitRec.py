import re

class UnitRec:
    def __init__(self):
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
        self.patterns = [
            '单位.{0,2}人民币(.{2,3})',
            '人民币(.{2,3})'
        ]

    def extract_unit(self, word):
        for pattern in self.patterns:
            finds = re.findall(pattern, word)
            if finds:
                if finds[0] in self.units:
                    return finds[0], self.units[finds[0]]

        return None, 1