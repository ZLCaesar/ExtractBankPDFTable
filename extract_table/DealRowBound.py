import re

# under_this = ['如下表所示', '明细如下', '情况如下', '单位.{0,2}人民币', '如下']
# start_from_this = ['\d{4}年']
# above_this = ['注:']

class DealBoundary:
    def __init__(self, under_this, start_from_this, above_this, bound_flag_dis_tolerance=2):
        """对于一个页面多个表格的页面，找到表与表之间的分界线；对于缺省了横线的表格，找到横线进行补充

        Args:
            under_this (list): 正则表达式list，符合该表达式的，则认为表的顶部坐标在此关键词底的下面
            start_from_this (list): 正则表达式list，符合该表达式的，则认为表的顶部坐标从此关键词顶开始
            above_this (list]): 正则表达式list，符合该表达式的，则认为表的底部坐标在此关键词顶的上面
            bound_flag_dis_tolerance (int, optional): 误差容忍值，例如表顶从“如下表所示”坐标的（bottom-bound_flag_dis_tolerance）开始. Defaults to 2.
        """
        self.UNDER_THIS = under_this
        self.START_FROM_THIS = start_from_this
        self.ABOVE_THIS = above_this
        self.BOUND_FLAG_DIS_TOLERANCE = bound_flag_dis_tolerance

    def get_bound_by_flag(self, words_list):
        def find_proper_line(bound):
            bound = sorted(bound, reverse=True)
            if len(bound)<2:
                return bound
            ret_arr = [bound[0]]
            before = bound[0]
            for i in range(1, len(bound)):
                if before-bound[i]>50:
                    ret_arr.append(bound[i])
                before = bound[i]

            return ret_arr
        upbound = []
        bottombound = []
        for word in words_list:
            text = word['text']
            if len(text)>16:
                continue
            top = word['top']
            bottom = word['bottom']
            find1, find2 = False, False
            
            for pattern in self.UNDER_THIS:
                if re.findall(pattern, text):
                    upbound.append(bottom-self.BOUND_FLAG_DIS_TOLERANCE)
                    find1 = True
                    break
            if find1:
                continue
                
            for pattern in self.START_FROM_THIS:
                if re.findall(pattern, text):
                    upbound.append(top+self.BOUND_FLAG_DIS_TOLERANCE)
                    find2 = True
                    break
            if find2:
                continue
                
            for pattern in self.ABOVE_THIS:
                if re.findall(pattern, text):
                    bottombound.append(top)
                    # find3 = True
                    break
        
        
        return find_proper_line(upbound), find_proper_line(bottombound)


    def get_table_boundary(self, y_split, upbound, bottombound):
        """
        一个页面可能有多个表格，根据纵坐标判断分了几个表格
        """
        # def reshape_yseq(y):
        #     for item in y:
        def change(a1, a2):
            if a1[1] == 'UP' or a1[1] == 'DOWN':
                a2[1] = a1[1]
                return a2, 0    #保留后者，删除当前
            elif a2[1] == 'UP' or a2[1] == 'DOWN':
                a1[1] = a2[1]
                return a1, 1    #保留当前，删除后者
            else:
                return None, -1
            
        def reshape_yseq(y):
            i = 0
            while i<len(y)-1:           
                if abs(float(y[i][0])-float(y[i+1][0]))<5:
                    value, pos = change(y[i], y[i+1])
                    if pos!=-1:
                        y.pop(i+pos)
                        i = i+pos
                        continue
                
                i += 1
        table_id = 0
        table_boundary = {}
        if len(y_split)<2:
            return {}
        y = sorted(y_split, reverse=True)
        y = [[item, None] for item in y]
        flags = [[item, 'UP'] for item in upbound]
        if not upbound:
            flags += [[item, 'DOWN'] for item in bottombound]  
        flag = -1
        while flags:
            flag = flags.pop(0)
            for i in range(len(y)):
                if y[i][0]<flag[0]:
                    y = y[:i]+[flag]+y[i:]
                    flag = -1
                    break
                else:
                    continue
        if flag != -1:
            y.append(flag)
        reshape_yseq(y)
        temp = []
        for i in range(0, len(y)):
            if y[i][1] == 'UP':
                if temp:
                    table_boundary[table_id] = temp
                table_id += 1
                temp = [y[i][0]]
            
            elif y[i][1] is None:
                temp.append(y[i][0])
            else:                         #DOWN
                temp.append(y[i][0])
                table_boundary[table_id] = temp
                temp = []
                
        if temp:
            table_boundary[table_id] = temp
            
        return table_boundary

    def find_proper_rows(self, top, bottom, words_list):
        def detect_insame_line(a, b):
            if a[0]>=b[0]>=a[1] and a[0]-b[0]<5:
                return True
            
            if b[0]>=a[0]>=b[1] and b[0]-a[0]<5:
                return True
            
            return False
        
        arr = []
        for word in words_list:
            if word['top']<top and word['bottom']>bottom:
                if not arr:
                    arr.append((word['top'], word['bottom']))
                elif detect_insame_line(arr[-1], (word['top'], word['bottom'])):
                    arr[-1] = (max(arr[-1][0], word['top']), min(arr[-1][1], word['bottom']))
                else:
                    arr.append((word['top'], word['bottom']))
        new_ylines = []
        for i in range(len(arr)-1):
            new_ylines.append(arr[i][1]+(arr[i+1][0]-arr[i][1])/2)
        return new_ylines