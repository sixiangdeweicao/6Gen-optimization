#coding:utf-8
'''
    APD别名前缀消除
    数据库两个表
    prefix
    predictIP

    1.前缀提取
        /32-/96 = 64 bit 
        python APD.py -extract -i [input.txt] -db [database] --begin=[begin] --end=[end]
    2.探测
        python APD.py --detectAll --database=[dbname] --threshold=[threshold] --IPv6=[IPv6] ----directory=[dirname] 
        python APD.py --detectOne --database [database] --threshold [threshold] --IPv6 [IPv6] ----directory [dirname]
    3.输出
        python APD.py --output --database=[db] > prefix.txt
'''
import argparse,code,sqlite3,random,json,time,os,subprocess
hex_list=['0','1','2','3','4','5','6','7','8','9','a','b','c','d','e','f']
def get_rawIP(IP):
    # 标准IP -> hex IP
    seglist=IP.split(':')
    if seglist[0]=='':
        seglist.pop(0)
    if seglist[-1]=='':
        seglist.pop()
    sup=8-len(seglist)
    if '' in seglist:
        sup+=1
    ret=[]
    for i in seglist:
        if i=='':
            for j in range(0,sup):
                ret.append('0'*4)
        else:
            ret.append('{:0>4}'.format(i))
    rawIP=''.join(ret)
    assert(len(rawIP)==32)
    return rawIP
def get_standardIP(hexIP):
    assert(len(hexIP) == 32)
    return ':'.join([hexIP[i: i + 4] for i in range(0, 32, 4)])
def get_standardPrefix(prefix):
    length=len(prefix)
    return ':'.join([prefix[i:i+4] for i in range(0,length,4)])+'::/'+str(length*4)
def generateTargets(prefix):
    length=len(prefix)
    comp_len=32-length-1
    # 32=length+1+()
    ret=[]
    for i in range(0,16):
        target=prefix+hex_list[i]
        for _ in range(comp_len):
            target+=hex_list[random.randint(0,15)]
        ret.append(target)
        assert(len(target)==32)
    return ret
def detectOne(database, threshold, dirname, local_IPv6):
    if not os.path.exists(dirname):
        os.mkdir(dirname)
    connection = sqlite3.connect(database)
    connection.execute('PRAGMA temp_store_directory = \'{}\';'.format(os.path.dirname(args.database)))
    #print(connection.execute('PRAGMA temp_store_directory;').fetchone()[0])
    cursor1 = connection.cursor()
    current_bitlength, begin, end = connection.execute('SELECT current_bitlength, begin, end FROM stat LIMIT 1;').fetchone()
    if current_bitlength == end:
        # 从Temp里创建
        tb_source = 'Temp'
    elif current_bitlength >= begin:
        tb_source = 'tb_{}'.format(current_bitlength + 4)
    else:
        print('alread scan all prefixed from {} to {}'.format(begin, end))
        return False
    # tb_dest 前缀， 匹配数量， 响应数量
    tb_dest = 'tb_{}'.format(current_bitlength)
    connection.executescript('DROP TABLE IF EXISTS {};CREATE TABLE {} (prefix TEXT, count INTEGER, response_count INTEGER);'.format(tb_dest, tb_dest))
    # tb_target 扫描IP 前缀 是否响应
    tb_target = 'target_{}'.format(current_bitlength)
    connection.executescript('DROP TABLE IF EXISTS {};CREATE TABLE {} (IP TEXT, prefix TEXT, responsive INTEGER);'.format(tb_target, tb_target))
    #print('current_bitlength {}, tb {}->{}'.format(current_bitlength, tb_source, tb_dest))
    oldprefix, prefix_count = '', 0
    t0 = time.time()
    if tb_source == 'Temp':
        for item in connection.execute('SELECT prefix FROM Temp ORDER BY prefix ASC;'):
            prefix = item[0]
            if oldprefix != prefix: 
                if prefix_count >= 1:
                    cursor1.execute('INSERT INTO {} VALUES (?, ?, ?);'.format(tb_dest), (oldprefix, prefix_count, 0))
                oldprefix = prefix
                prefix_count = 1
            else:
                prefix_count += 1
        if prefix_count >= 1:
            cursor1.execute('INSERT INTO {} VALUES (?, ?, ?);'.format(tb_dest), (oldprefix, prefix_count, 0))
        #print('create tbdest use {} seconds'.format(time.time() - t0))
        t0 = time.time()
        cursor1.execute('CREATE INDEX {} ON {}(prefix);'.format(tb_dest+'index', tb_dest))
        #print('create index use {} seconds'.format(time.time() - t0))
    else:
        # already sorted
        isAliased = True
        for item in connection.execute('SELECT prefix, count, response_count FROM {};'.format(tb_source)):
            prefix, add_count, response_count = item[0][:current_bitlength / 4], item[1], item[2]
            # 非别名
            if (response_count >= 0 and response_count < 16) or (response_count == -1): 
                isAliased = False
            if oldprefix != prefix:
                if prefix_count >= 1:
                    # 需要扫描
                    if isAliased:
                        cursor1.execute('INSERT INTO {} VALUES (?, ?, ?);'.format(tb_dest), (oldprefix, prefix_count, 0))
                    else:
                        cursor1.execute('INSERT INTO {} VALUES (?, ?, ?);'.format(tb_dest), (oldprefix, prefix_count, -1))
                oldprefix = prefix
                prefix_count = add_count
                if response_count == 16:
                    isAliased = True
            else:
                prefix_count += add_count
        if prefix_count >= 1:
            # 需要扫描
            if isAliased:
                cursor1.execute('INSERT INTO {} VALUES (?, ?, ?);'.format(tb_dest), (oldprefix, prefix_count, 0))
            else:
                cursor1.execute('INSERT INTO {} VALUES (?, ?, ?);'.format(tb_dest), (oldprefix, prefix_count, -1))
        #print('create tbdest use {} seconds'.format(time.time() - t0))
        t0 = time.time()
        cursor1.execute('CREATE INDEX {} ON {}(prefix);'.format(tb_dest+'index', tb_dest))
        #print('create index use {} seconds'.format(time.time() - t0))
    #print('creating new table use {} seconds'.format(time.time() - t0))
    target_filename = '{}/target-{}.txt'.format(dirname, current_bitlength)
    result_filename = '{}/result-{}.txt'.format(dirname, current_bitlength)
    filecount = 0
    t0 = time.time()
    with open(target_filename, 'w') as f:
        for item in connection.execute('SELECT prefix, count, response_count FROM {};'.format(tb_dest)):
            prefix, count, response_count = item[0], item[1], item[2]
            if response_count == 0:
                if count >= threshold:
                    targets = generateTargets(prefix)
                    for target in targets:
                        standardIP = get_standardIP(target)
                        connection.execute('INSERT INTO {} VALUES (?, ?, ?);'.format(tb_target), (target, prefix, 0))
                        f.write(standardIP + '\n')
                        filecount += 1
                else:
                    connection.execute('UPDATE {} SET response_count = -2 WHERE prefix = ?;'.format(tb_dest), (prefix,))
    #print('writing to target_file use {} seconds'.format(time.time() - t0))
    if filecount == 0:
        print('skip at {}'.format(current_bitlength))
    else:
        t0 = time.time()
        cursor1.execute('CREATE INDEX {} ON {}(IP);'.format(tb_target+'index', tb_target))
        #print('create index on targets.IP use {} seconds'.format(time.time() - t0))
        command = 'sudo zmap --ipv6-target-file={} --ipv6-source-ip={} -M icmp6_echoscan -f saddr,daddr,ipid,ttl,timestamp_str -O json -o {}'.format(target_filename, local_IPv6, result_filename)
        t0 = time.time()
        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        returncode = p.poll()
        while returncode is None:
            line = p.stdout.readline()
            returncode = p.poll()
            line = line.strip()
            #print(line)
        print('zmap scanning {}, store result in {},use {} seconds'.format(target_filename, result_filename, time.time() - t0))
        t0 = time.time()
        for line in open(result_filename, 'r'):
            responsive_IP=json.loads(line)['saddr']
            raw_IP=get_rawIP(responsive_IP)
            prefix=connection.execute('select prefix from {} where IP=?;'.format(tb_target),(raw_IP,)).fetchone()[0]
            connection.execute('update {} set responsive=1 where IP=?;'.format(tb_target),(raw_IP,))
            connection.execute('update {} set response_count=response_count+1 where prefix=?;'.format(tb_dest),(prefix,))
        for prefix_ in connection.execute('select prefix from {} where response_count=16;'.format(tb_dest)):
            cursor1.execute('INSERT INTO AliasedPrefixes VALUES (?);', (prefix_[0],))
    connection.execute('UPDATE stat SET current_bitlength = current_bitlength - 4;')
    connection.commit()
    connection.close()
    return True
def test(database):
    connection=sqlite3.connect(database)
    connection.execute('PRAGMA temp_store_directory = \'{}\';'.format(os.path.dirname(database)))
    t0=time.time()
    f=open('test.t','w')
    count = 0
    for item in connection.execute('SELECT prefix FROM Temp ORDER BY prefix ASC;'):
        f.write(item[0][0])
        count += 1
        if count % 1000000 == 0:
            print('{} use {} seconds'.format(count, time.time() - t0))
    f.close()
    print('{} use {} seconds'.format(count, time.time() - t0))
    connection.commit()
    connection.close()
    exit(0)
def extract(input, database, begin, end):
    # 统计 prefix, count, 0
    t0,IP_count=time.time(),0
    begin_hex, end_hex = begin / 4, end / 4
    connection=sqlite3.connect(database)
    connection.execute('PRAGMA temp_store_directory = \'{}\';'.format(os.path.dirname(database)))
    print(connection.execute('PRAGMA temp_store_directory;').fetchone()[0])
    connection.executescript('DROP TABLE IF EXISTS stat;create table stat (current_bitlength INTEGER, IP_count INTEGER, begin INTEGER, end INTEGER, threshold INTEGER);')
    connection.executescript('DROP TABLE IF EXISTS Temp; CREATE TABLE Temp (prefix TEXT);')
    connection.executescript('DROP TABLE IF EXISTS AliasedPrefixes; CREATE TABLE AliasedPrefixes (prefix TEXT);')
    c1,c2=connection.cursor(),connection.cursor()
    batches, max_count = [], 10000000
    for line in open(input):
        if line and line[0]!='#':
            IP=line.strip()
            raw_IP=get_rawIP(IP)
            #assert(len(raw_IP) == 32)
            IP_count+=1
            if IP_count%1000000==0:
                print('{} {} seconds'.format(IP_count, time.time()-t0))
            prefix = raw_IP[:end_hex]
            batches.append((prefix, ))
            if len(batches) >= max_count:
                c1.executemany('INSERT INTO Temp VALUES (?);', batches)
                batches = []
    c1.executemany('INSERT INTO Temp VALUES (?);', batches)
    t0 = time.time()
    c1.execute('CREATE INDEX Temp_Index ON Temp(prefix);')
    print('create index use {} seconds'.format(time.time() - t0))
    connection.execute('INSERT INTO stat values (?, ?, ?, ?, ?);', (end, IP_count, begin, end, 0))
    connection.commit()
    connection.close()
if __name__=='__main__':
    # parse=argparse.ArgumentParser()
    # parse.add_argument('--extract', action='store_true', help='extract prefix to db file')
    # parse.add_argument('--test', action='store_true', help='do some test.')
    # parse.add_argument('--detectOne', action='store_true', help='after extract')
    # parse.add_argument('--detectAll', action='store_true', help='after extract')
    # parse.add_argument('--output', action='store_true', help='print aliased prefix')
    # parse.add_argument('--input','-i',type=str,help='input IPv6 addresses. # to comment \\n to split. or dbfile or prefix file')
    # parse.add_argument('--database','-db',type=str,help='output database name')
    # parse.add_argument('--directory','-tempdir',type=str,help='output directory name')
    # parse.add_argument('--IPv6','-IP',type=str,help='local IPv6 address')
    # parse.add_argument('--threshold','-t',default=100,type=int,help='threshold, min prefix count')
    # parse.add_argument('--begin','-b',default=32,type=int,help='prefix range')
    # parse.add_argument('--end','-e',default=96,type=int,help='prefix range')
    # args=parse.parse_args()

    # if args.detectOne:
    #     detectOne(args.database, args.threshold, args.directory, args.IPv6)
    # elif args.detectAll:
    #     while detectOne(args.database, args.threshold, args.directory, args.IPv6):
    #         #print('')
    #         pass
    # elif args.extract:
    #     extract(args.input, args.database, args.begin, args.end)
    # elif args.output:
    #     # 输出别名前缀
    #     connection=sqlite3.connect(args.database)
    #     for item in connection.execute('SELECT prefix FROM AliasedPrefixes;'):
    #         print(get_standardPrefix(item[0]))
    #     connection.close()
    # elif args.test:
    #     test(args.database)
    print(get_rawIP('2001:da8::2:abc'))
    print(get_standardIP(get_rawIP('2001:da8::2:abc')))