#coding: utf-8
# python patternMining.py --read [filename] --write [filename] --budgets [budgetlist] --depth [depth] --experience=[True/False]
from __future__ import print_function
from collections import deque
import numpy as np
import argparse, code, time, math, resource
bit_list=['0','f']
EUIbegin, EUIend, EUIfffe = 22, 26, 'fffe'
OUIbegin, OUIend = 16, 22

BAD_CLASSIFY_BUCKET_INDEX=32
SINGLE_BUCKET_INDEX=33
DENSE_BUCKET = 34

def isLowBytes(IP):
    # 返回是LB，LB的类型
    compress=[]
    count=0
    for i in range(4):
        print(16+i*4)
        former_f=IP[16+i*4]
        bit_=former_f
        for j in range(4):
            print(16+i*4+j)
            f = IP[16 + i * 4 + j]
            if f not in bit_list:
                bit_='2'
                break
            elif j!=0:
                if f!=former_f:
                    bit_='2'
                    break
        if bit_=='0':
            compress.append('0')
            count+=1
        elif bit_=='f':
            compress.append('1')
            count+=1
        elif bit_=='2':
            compress.append('2')
    tagvalue=int(''.join(compress), 3)
    return (count>=2), tagvalue

def reverseOUI(OUI):
    v = int(OUI[1], 16)
    if v & 2 != 0: v-=2
    else: v+=2
    return OUI[0]+hex(v)[-1]+OUI[2:]

def isEUI(IP, EUIdist, OUIs, threshold = 2):
    if IP[EUIbegin : EUIend] != EUIfffe: return False
    OUI_unprocessed = IP[OUIbegin : OUIend]
    OUI_processed = reverseOUI(OUI_unprocessed)
    if OUI_unprocessed not in EUIdist and OUI_processed not in OUIs: 
        return False
    elif OUI_processed not in OUIs and OUI_unprocessed in EUIdist and EUIdist[OUI_unprocessed] < threshold: 
        return False
    return True
def init_EUI_dist(IPs, EUIdist):
    for IP in IPs:
        if IP[EUIbegin : EUIend] == EUIfffe:
            OUI_unprocessed = IP[OUIbegin : OUIend]
            if OUI_unprocessed not in EUIdist:
                EUIdist[OUI_unprocessed] = 1
            else:
                EUIdist[OUI_unprocessed] += 1
def read_OUIFile(OUIFile):
    ret = set()
    for line in open(OUIFile):
        if line and 'base 16' in line:
            OUI=line.split(' ')[0]
            ret.add(OUI.lower())
    return ret
def hexDistribution(IPs, index):
    ret={}
    for s in [IP[index] for IP in IPs]:
        if s not in ret:
            ret[s] = 1
        else:
            ret[s] += 1
    retList = [[v, k] for k, v in ret.items()]
    return retList

def splitUsingExperience(IPs, filename='/home/liguo/ipv6-research/oui.txt'):
    LB, EUI, Other = {}, [], []
    EUIdist = {}
    init_EUI_dist(IPs, EUIdist)
    OUIs = read_OUIFile(filename)
    for IP in IPs:
        isLB_, tagvalue = isLowBytes(IP) 
        if isLB_:
            if tagvalue not in LB:
                LB[tagvalue] = [IP]
            else:
                LB[tagvalue].append(IP)
        elif isEUI(IP, EUIdist, OUIs, 2):
            EUI.append(IP)
        else:
            Other.append(IP)
    ret = [EUI, Other]
    ret.extend(LB.values())
    return ret

def show_buckets(buckets):
    print('show bucket!:')
    for i, bucket in enumerate(buckets):
        if len(bucket) == 0: continue
        print('bucket {} {}'.format(i, len(bucket)))
        if i == 33:
            for IP in bucket:
                print(IP)
        else:
            for item in bucket:
                pattern, count = item[1], len(item[0])
                Length = getVarLength(pattern)
                density = (float)(count) / 16 ** Length
                if density >= 0.01:
                    continue
                print('pattern {},{} count {} density {}'.format(pattern, Length, count, density))

def get_var_position(pattern):
    #获取pattern中x的下标
    ret = []
    for i, v in enumerate(pattern):
        if v == 'x':
            ret.append(i)
    return ret

def getValueOf(IPs, pattern):
    values = []
    var_index_list = get_var_position(pattern)
    for IP in IPs:
        s = ''.join([IP[index] for index in var_index_list])
        if s == '':
            continue
        values.append(int(s, 16))
    return values

def collect_var_pattern(IPs, pattern):
    # 检查pattern中可变的位
    var_index_list = get_var_position(pattern)
    pattern = [s for s in pattern]
    for i in var_index_list:
        hD = hexDistribution(IPs, i)
        if len(hD) == 1:
            pattern[i] = hD[0][1]
    return ''.join(pattern)

def get_density_item(IPs, pattern):
    # generate item for predict
    var_pattern_ = collect_var_pattern(IPs, pattern)
    var_index_list = get_var_position(var_pattern_)
    var_patterns = [] # 变化部分
    for IP in IPs:
        s = ''.join([IP[i] for i in var_index_list])
        var_patterns.append(s)
    min_pattern, max_pattern = var_patterns[0], var_patterns[0]
    for var_pattern in var_patterns:
        if var_pattern > max_pattern:
            max_pattern = var_pattern
        if var_pattern < min_pattern:
            min_pattern = var_pattern
    density = (float)(len(IPs)) / (int(max_pattern, 16) - int(min_pattern, 16) + 1)
    if density == 1:
        min_pattern = min_pattern[:-1] + '0'
        max_pattern = max_pattern[:-1] + 'f'
        density = (float)(len(IPs)) / (int(max_pattern, 16) - int(min_pattern, 16) + 1)
    if density == 1:
        return []
    return [IPs, var_pattern_, min_pattern, max_pattern, density]

def find_continuous_regions(values, eps, min_pts):
    length = len(values)
    if length <= 1:
        return []
    ret = []
    begin_index, end_index = 0, 0
    count_ = 0
    o_value, n_value = values[0], 0
    while 1:
        if end_index == 0:
            n_value = values[0]
            count_ += 1
        else:
            n_value = values[end_index]
            if n_value - o_value <= eps:
                count_ += 1
            else:
                if count_ >= min_pts:
                    ret.append([begin_index, end_index - 1])
                count_ = 0
                begin_index = end_index
            o_value = n_value
        end_index += 1
        if end_index == length:
            if count_ >= min_pts:
                ret.append([begin_index, end_index - 1])
            break
    return ret

def find_dense_regions(it):
    dense_regions = []
    label_regions = {}
    IPs, pattern = it[0], it[1]
    varLength = getVarLength(pattern)
    length = len(IPs)
    if length <= 1 or varLength <= 0:
        #print('find_dense_regions IP count {} varLength {}'.format(length, varLength))
        return []
    values = getValueOf(IPs, pattern)
    values = np.array(values)
    index_sort = values.argsort()
    sorted_values = values[index_sort]
    continuous_regions = find_continuous_regions(sorted_values, 16, 3)
    for region in continuous_regions:
        lindex, rindex = region[0], region[1]
        IP_list = [IPs[index_sort[index]] for index in range(lindex, rindex + 1)]
        if len(IP_list) == 0:
            continue
        item = get_density_item(IP_list, pattern)
        if len(item) > 0:
            dense_regions.append(item)
    return dense_regions

def getPattern(IPs):
    # 返回pattern和不变的位数量
    if len(IPs) == 1:
        return IPs[0], 32
    pattern, fixLength = [], 0
    for i in range(32):
        hexDist = hexDistribution(IPs, i)
        if len(hexDist) == 1:
            pattern.append(hexDist[0][1])
            fixLength += 1
        else:
            pattern.append('x')
    pattern = ''.join(pattern)
    return pattern, fixLength
def getVarLength(pattern):
    # 获取变化的位数量
    return sum([1 if i == 'x' else 0 for i in pattern])
def getFixLength(pattern):
    # 获取不变的位数量
    return sum([1 if i != 'x' else 0 for i in pattern])
def getRange(pattern):
    varLength = sum([1 if i == 'x' else 0 for i in pattern])
    return 16 ** varLength
def getEntropy(problist):
    return sum([-prob * math.log(prob) if prob != 0 else 0 for prob in problist])
def findNext(pattern, begin):
    # 找到大于begin的x区间
    pos = str.find(pattern, 'x', begin)
    beg = pos
    while pos + 1 < 32 and pattern[pos + 1] == 'x':
        pos += 1
    return beg, pos
def var_areas(pattern):
    areas = []
    begin = 0
    while True:
        beg, end = findNext(pattern, begin)
        if beg != -1:
            areas.append([beg, end])
            begin = end + 1
        else:
            break
    return areas
def findMaxLength(pattern, limit = 4):
    temp = []
    begin = 0
    while True:
        beg, end = findNext(pattern, begin)
        if beg == -1: break
        temp.append([beg, end - beg + 1])
        begin = end + 1
    # 连续区间集合
    temp.sort(key=lambda item: item[1], reverse=True)
    Length = min(temp[0][1], limit)
    ret = []
    # 避免过多的次数
    if Length <= 4:
        step = 1
    else:
        step = 2
    for item in temp:
        # 区间比最大限制大
        if item[1] > Length:
            for i in range(0, item[1] - Length + 1, step):
                ret.append(item[0] + i)
            continue
        if item[1] < Length: break
        ret.append(item[0])
    return ret, Length
def findBestSplit(IPs, begins, length):
    Total = (float)(len(IPs))
    best_entropy = float('inf')
    best_begin = -1
    best_split = {}
    for begin in begins:
        current_split = {}
        for IP in IPs:
            pattern = IP[begin:begin+length]
            if not pattern in current_split:
                current_split[pattern] = [IP]
            else:
                current_split[pattern].append(IP)
        problist = [len(IPList) / Total for IPList in current_split.values()]
        entropy = getEntropy(problist)
        if entropy < best_entropy:
            best_entropy = entropy
            best_split = current_split.values()
            best_begin = begin
    return best_split, best_begin

def fun_split_IPs(IPs, pattern, limit):
    length = len(IPs)
    if length <= 1:
        return [], 0, 0
    varLength = getVarLength(pattern)
    if limit <= 0:
        if varLength >= 16:
            limit = 4
        else:
            limit = 1
    array, maxLength = findMaxLength(pattern, limit)
    splitIPs, begin = findBestSplit(IPs, array, maxLength)
    return splitIPs, begin, maxLength

def expand(IPs, pattern, buckets, limit, debug=False):
    # 当前结点是否要进行划分？？
    splitIPs, begin, maxLength = fun_split_IPs(IPs, pattern, limit)
    if len(splitIPs) == 0:
        return
    fixLength_top = getFixLength(pattern)
    singleIPs = []
    if maxLength >= 4:
        threshold = 2
    else:
        threshold = 1
    # 保留非随机的子结点，
    # 其他以当前pattern放入备用桶1， 放入备用桶2
    # 其他：密度小；误分类
    for IPList in splitIPs:
        length = len(IPList)
        if length <= threshold:
            singleIPs.extend(IPList)
        elif length > threshold:
            pattern_, fixLength = getPattern(IPList)
            buckets[fixLength].append([IPList, pattern_])
    if len(singleIPs) == 1:
        buckets[SINGLE_BUCKET_INDEX].extend(singleIPs)
        return
    pattern_, fixLength = getPattern(singleIPs)
    if fixLength == fixLength_top: # 密度小
        buckets[BAD_CLASSIFY_BUCKET_INDEX].append([singleIPs, pattern_])
    else: # 误分类
        buckets[fixLength].append([singleIPs, pattern_])
    

def increase_density(buckets, min_density):
    # 识别连续区域
    t0 = time.time()
    for i, bucket in enumerate(buckets):
        if i == DENSE_BUCKET or i == SINGLE_BUCKET_INDEX:
            continue
        else:
            for j, item in enumerate(bucket):
                if len(item) <= 1: # ignore invalidate item
                    continue
                IP_count = len(item[0])
                pattern = item[1]
                rangeSize = getRange(pattern)
                density = IP_count / (float)(rangeSize)
                if density >= min_density: continue
                dense_regions = find_dense_regions(item)
                region_count = len(dense_regions)
                if region_count > 0:
                    buckets[DENSE_BUCKET].extend(dense_regions)
                    bucket[j] = [] # invalidate item
    print('increase count {} , {} seconds'.format(len(buckets[DENSE_BUCKET]), time.time() - t0))

def regen_pattern(buckets, limit):
    # 对于密度小的再次进行分类
    # use bad bucket
    t0 = time.time()
    replace_bucket = buckets[BAD_CLASSIFY_BUCKET_INDEX]
    buckets[BAD_CLASSIFY_BUCKET_INDEX] = deque()
    while 1:
        if len(replace_bucket) == 0: break
        it = replace_bucket.popleft()
        if len(it) == 0:
            continue
        IPs, pattern = it[0], it[1]
        expand(IPs, pattern, buckets, limit)
    print("=====分割线====")
    # use single bucket
    IPs = buckets[SINGLE_BUCKET_INDEX]
    buckets[SINGLE_BUCKET_INDEX] = deque()
    pattern_, fixLength_ = getPattern(IPs)
    expand(IPs, pattern_, buckets, limit)
    print('regen_pattern count , {} seconds'.format(time.time() - t0))

def process(IPs, budgets, depth, filename, prior_experience, limit, retrain, increase):
    # depth 展开到多少位
    # buckets[i]:i位固定的集合
    # i = 32 容纳处理地址
    # i=33 容纳singleIP
    # i=34 容纳密度大的集合
    budgets.sort(reverse=True)
    budget_index = 0
    budget = budgets[budget_index]
    buckets = []
    for i in range(35):
        buckets.append(deque())
    #buckets.append(deque())
    if prior_experience:
        t0 = time.time()
        split_IPs = splitUsingExperience(IPs)
        currentBucket = 34
        for IPList in split_IPs:
            if len(IPList) == 1:
                buckets[SINGLE_BUCKET_INDEX].extend(IPList)
                continue
            elif len(IPList) == 0:
                continue
            currentPattern, fixLength = getPattern(IPList)
            buckets[fixLength].append([IPList, currentPattern])
            if currentBucket > fixLength:
                currentBucket = fixLength
            print('pattern {}, fixlength {}, include {} IPs'.format(currentPattern, fixLength, len(IPList)))
        print('experience {} seconds'.format(time.time() - t0))
    else:
        currentPattern, fixLength = getPattern(IPs)
        buckets[fixLength].append([IPs, currentPattern])
        currentBucket = fixLength
        print('no experience {} {}'.format(currentPattern, fixLength))
    t0=time.time()
    expandLevel = min(32 - depth, 31)
    exitLimit = 1
    exitFlag = 0
    while True:
        # 展开 结束条件： currentBucket >= 32
        while 1:
            if currentBucket >= expandLevel:
                break
            bucketCount = len(buckets[currentBucket])
            if bucketCount == 0: 
                currentBucket += 1
            elif len(buckets[currentBucket][0]) == 0:
                buckets[currentBucket].popleft()
                continue
            else:
                break
        if currentBucket >= expandLevel:
            if exitFlag == exitLimit:
                print('Bucket {}'.format(currentBucket))
                break
            else:
                if increase:
                    TargetList=[]
                    target_gen(TargetList, buckets)
                    minimum_density = getMinimumDensity(TargetList, budget)
                    increase_density(buckets, minimum_density)
                if retrain:
                    regen_pattern(buckets, limit)
                exitFlag += 1
                currentBucket = 0
                continue
        t0 = time.time()
        item = buckets[currentBucket].popleft()
        IPs, pattern = item[0], item[1]
        expand(IPs, pattern, buckets, limit)
        t1 = time.time() - t0
        if t1 > 10:
            print('expand bucket {} use {} seconds'.format(currentBucket, t1))
    #show_buckets(buckets)
    if budget_index >= len(budgets):
        return
    TargetList=[]
    max_range_ = target_gen(TargetList, buckets)
    print('Total max range is {}'.format(max_range_))
    for i in range(budget_index, len(budgets)):
        budget = budgets[i]
        predict(filename+'.'+str(budget), budget, TargetList)

def expand_dense_pattern(pattern, min_pattern, max_pattern):
    var_index_list = get_var_position(pattern)
    length = len(var_index_list)
    pattern = [i for i in pattern]
    begin, end = int(min_pattern, 16), int(max_pattern, 16)
    for i in range(begin, end + 1):
        hex_part = hex(i)[2:]
        hex_length = len(hex_part)
        var_str = '0' * (length - hex_length) + hex_part
        for i, index in enumerate(var_index_list):
            pattern[index] = var_str[i]
        yield ''.join(pattern)
    raise StopIteration

def target_gen(TargetList, buckets):
    range_ = 0
    for i, bucket in enumerate(buckets):
        if i == DENSE_BUCKET:
            for item in bucket:
                IPs, var_pattern_, min_pattern, max_pattern, density = item[0], item[1], item[2], item[3], item[4]
                TargetList.append([density, var_pattern_, min_pattern, max_pattern])
                range_ += int(max_pattern,16) - int(min_pattern,16) + 1
        elif i == SINGLE_BUCKET_INDEX:
            continue
        else:
            for item in bucket:
                if len(item) <= 1: # ignore invalidate item
                    continue
                pattern = item[1]
                count_ = len(item[0])
                if count_ <= 1: continue
                pattern_range_ = getRange(pattern)
                range_ += pattern_range_
                density = (float)(count_) / pattern_range_
                TargetList.append([density, pattern])
    TargetList.sort(key = lambda item: item[0], reverse=True)
    return range_

def getMinimumDensity(TargetList, budget):
    count = 0
    minimum_density = 0.0
    for item in TargetList:
        density, pattern = item[0], item[1]
        minimum_density = density
        if density == 1.0: continue
        if len(item) == 2:
            pattern_range = getRange(pattern)
            count += pattern_range
        elif len(item) == 4:
            min_pattern, max_pattern = item[2], item[3]
            pattern_range = int(max_pattern, 16) - int(min_pattern, 16) + 1
            count += pattern_range
        if count >= budget:
            break
    return minimum_density

def predict(filename, budget, TargetList):
    t0 = time.time()
    print('=============\npredict for {} at budget {}'.format(filename, budget))
    f2=open(filename+'.pattern', 'w')
    writecount = 0
    exactcount = 0.0
    for item in TargetList:
        density, pattern = item[0], item[1]
        if density == 1.0: 
            #print('pattern {} density = 1.0'.format(pattern))
            continue
        if len(item) == 2:
            pattern_range = getRange(pattern)
            exactcount += pattern_range * density
            if writecount + pattern_range > budget:
                predict_count = budget - writecount
            else:
                predict_count = pattern_range
            f2.write('*{} {} {}\n'.format(pattern, predict_count, density))
            writecount += pattern_range
        elif len(item) == 4:
            min_pattern, max_pattern = item[2], item[3]
            pattern_range = int(max_pattern, 16) - int(min_pattern, 16) + 1
            exactcount += pattern_range * density
            f2.write('{} {}-{} {}\n'.format(pattern, min_pattern, max_pattern, density))
            writecount += pattern_range
        if writecount > budget:
            break
    if writecount > 0:
        if writecount > budget:
            f2.write('generate {}/{} density {}'.format(exactcount, budget, exactcount / budget))
        else:
            f2.write('generate {}/{} density {}'.format(exactcount, writecount, exactcount / writecount))
    f2.close()
    print('============ {} seconds'.format(time.time() - t0))

def limit_memory(maxsize):
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (maxsize, hard))
    
if __name__=='__main__':
    limit_memory(4*2**30)
    parse=argparse.ArgumentParser()
    parse.add_argument('--read',type=str,help='input hex IPv6 . # to comment \\n to split')
    parse.add_argument('--budgets',type=int,nargs='+',help='input budget list')
    parse.add_argument('--depth',type=int,default=4,help='input budget')
    parse.add_argument('--write',type=str,help='input hex IPv6 . # to comment \\n to split')
    parse.add_argument('--experience',type=str,help='True:use LB and EUI64, False: simple one.')
    parse.add_argument('--limit',type=int,help='split limit ')
    parse.add_argument('--retrain',type=str,default='True',help='retrain bad seeds')
    parse.add_argument('--increase',type=str,default='True',help='find dense regions in low density seeds')
    parse.add_argument('--env',action='store_true',help='')
    args=parse.parse_args()
    if args.env:
        code.interact(banner = "", local = dict(globals(), **locals()))
        exit(0)
    remain_count = 10000000

    IPs=[]
    t0=time.time()
    count_ = 0
    for line in open(args.read):
        if line and line[0]!='#':
            IP=line.strip()
            count_ += 1
            if count_ <= remain_count:
                IPs.append(IP)
            else:
                break
    IPs=list(set(IPs))
    print('read {} IP use {} seconds'.format(len(IPs), time.time() - t0))

    t0=time.time()
    if args.limit != None:
        limit = args.limit
    else:
        limit = 0
    if args.retrain == 'True':
        retrain = True
    else:
        retrain = False
    if args.increase == 'True':
        increase = True
    else:
        increase = False

    process(IPs, args.budgets, args.depth, args.write, (args.experience == 'True'), limit, retrain, increase)
    print('total use {} seconds'.format(time.time() - t0))






