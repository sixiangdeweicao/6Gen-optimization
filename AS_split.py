#coding:utf-8
'''
    准备：
        pyasn安装
        IPv6RIB文件下载 （pyasn_util_download.py -6）
    输入：
        文件名：包含IPv6地址 #为注释
        目标文件夹名：若不存在则创建
    输出：
        1.生成数据库
            python AS_split.py --src [filename] --dst [dirname] --dat ipasn_20190402.dat
        2.统计比例
            python AS_split.py -analyze --min [min] --dst [dirname]
        3.提取数据
            python AS_split.py -split --dst [dirname] --mode [AS] --value 4
'''
import pyasn,argparse,os,time,code,sqlite3,sys
import matplotlib.pyplot as plt
import numpy as np

def read_IPs(filename,IPASN_filename,connection):
    '''
        不去重,忽略#号行,ASN -1表示IPASN无法分类的IP地址
    '''
    c=connection.cursor()
    c.execute('''DROP TABLE IF EXISTS IPs''')
    c.execute('''create table IPs(address TEXT(41),AS_number INTEGER(8))''')
    asndb=pyasn.pyasn(IPASN_filename)
    t0=time.time()
    IP_count=0
    batches,max_batch=[],2000000
    for line in open(filename,'r'):
        if not line or line[0]=='#' or line[0]=='\n': continue
        IP=line.strip()
        AS_number,prefix_str=asndb.lookup(IP)
        if AS_number==None:
            AS_number=-1
        batches.append((IP,AS_number))
        IP_count+=1
        if len(batches)==max_batch:
            c.executemany('insert into IPs values (?,?)',batches)    
            batches=[]
            print('every {} needs {} seconds'.format(max_batch,time.time()-t0))
            t0=time.time()
    c.executemany('insert into IPs values (?,?)',batches)
    t0=time.time()
    c.execute('create index AS_INDEX on IPs (AS_number)')
    connection.commit()
    print('create index use {} seconds'.format(time.time()-t0))
    return IP_count

def statistics(dirname, IP_count, connection, minimum):
    c1,c2=connection.cursor(),connection.cursor()
    t0=time.time()
    filename='ASN_statistics.txt'
    f=open('{}/{}'.format(dirname,filename),'w')
    f.write('AS_number  IP_number  IP_percentage\n')
    sorted_list=[]
    ignore_count=0
    for item in c1.execute('select distinct AS_number from IPs'):
        AS_number=item[0]
        count=c2.execute('select count(*) from IPs where AS_number=?',(AS_number,)).fetchone()[0]
        if count<minimum: ignore_count+=count
        if AS_number!=-1:
            sorted_list.append([AS_number,count])
    sorted_list.sort(key=lambda x:x[1],reverse=True)
    for item in sorted_list:
        f.write('{:10d} {:10d} {}\n'.format(item[0],item[1],item[1]/(float)(IP_count)))
    Ncount=c1.execute('select count(*) from IPs where AS_number=-1').fetchone()[0]
    f.write('IPs in one AS less than {} sum={}, percentage={}\n'.format(minimum,ignore_count,ignore_count/(float)(IP_count+1)))
    f.write('\nIPs without AS number: count={}, percentage={}\n'.format(Ncount,Ncount/(float)(IP_count+1)))
    f.close()
    ASN_count,current=len(sorted_list),0
    axe_Y=[]
    
    for i in range(0,ASN_count):
        current+=sorted_list[i][1]
        axe_Y.append(current/(float)(IP_count))
    #code.interact(banner = "", local = dict(globals(), **locals()))
    axe_X=range(1,ASN_count+1)
    fig=plt.figure()
    plt.plot(axe_X,axe_Y)
    plt.xlabel('AS count')
    plt.ylabel('IP percentage')
    #plt.grid(True, linestyle = "-.", color = "r", linewidth = "3")
    #plt.xlim(0.0,30.0)
    plt.savefig('{}/percentage.jpg'.format(dirname))
    plt.close(fig)
    sum_array = np.array([i[1] for i in sorted_list])
    plt.figure()
    plt.pie(x=sum_array,autopct='%.2f%%')
    plt.savefig('{}/bintu.jpg'.format(dirname))
    print('statistics use {} seconds'.format(time.time()-t0))
    return

def split_IPs(dirname, IP_count, connection, mode, n):
    #第一行 IP_count percentage
    print('start split_IPs:')
    t0=time.time()
    c1,c2=connection.cursor(),connection.cursor()
    sorted_list=[]
    for item in c1.execute('select distinct AS_number from IPs'):
        AS_number=item[0]
        IP_num=c2.execute('select count(*) from IPs where AS_number=?',(AS_number,)).fetchone()[0]
        sorted_list.append([AS_number, IP_num])
    sorted_list.sort(key=lambda x:x[1], reverse=True)
    if mode=='AS':
        n = (int)(n)
        target_list=sorted_list[:n]
    elif mode=='percent':
        target_list=[]
        count=0.0
        for item in sorted_list:
            count+=item[1]
            target_list.append(item)
            if count/IP_count>=n:
                break
    print('tl use {} seconds'.format(time.time()-t0))
    print('target_list len={}'.format(len(target_list)))
    t0=time.time()
    t=time.time()
    for item in target_list:
        AS_number, IP_num = item[0], item[1]
        f=open('{}/AS{}.txt'.format(dirname,AS_number),'w')
        f.write('#AS number={}, IP number={}\n'.format(AS_number,IP_num))
        IP_batches,max_batch=[],10000
        for address_t in c2.execute('select address from IPs INDEXED BY AS_INDEX where AS_number=?',(AS_number,)):
            IP=address_t[0]
            IP_batches.append(IP)
            if len(IP_batches)==max_batch:
                f.write('\n'.join(IP_batches)+'\n')
                IP_batches=[]
        f.write('\n'.join(IP_batches))
        f.close()
        print('file ASN {}, count {}, use {} seconds'.format(AS_number,IP_num,time.time()-t))
        t=time.time()
    print('split_IPs use {} seconds'.format(time.time()-t0))
    return

if __name__=='__main__':

    parse=argparse.ArgumentParser()
    parse.add_argument('--src','-s',type=str,help='input IPv6 addresses. # to comment \\n to split')
    parse.add_argument('-analyze', action='store_true',help='load data and analyze')
    parse.add_argument('-split', action='store_true',help='divide IP by ASN')
    parse.add_argument('--dst','-d',type=str,help='result directory name without /')
    parse.add_argument('--dat',default='ipasn_20190730.dat',type=str,help='IPASN Data File, see details at https://github.com/hadiasghari/pyasn.')
    parse.add_argument('--min','-m',default=100000,type=int,help='AS IP min count.')
    parse.add_argument('--mode',default='percent',type=str,help='percent|AS')
    parse.add_argument('--value',default=0.9,type=float,help='percent|AS')
    args=parse.parse_args()
    if args.dst==None:
        exit(0)
    if not os.path.exists(args.dst):
        os.mkdir(args.dst)
    connection=sqlite3.connect('{}/AS_split.db'.format(args.dst))

    # read IP and use pyasn-> store to test.db.IPs (address,AS_number)
    if args.src!=None:
        IP_count=read_IPs(args.src,args.dat,connection)
    else:
        IP_count=connection.execute('select count(*) from IPs;').fetchone()[0]
    if args.analyze:
        statistics(args.dst,IP_count,connection,args.min)
    if args.split:
        #split_IPs(args.dst,IP_count,connection,'IP percent',0.9)
        split_IPs(args.dst,IP_count,connection, args.mode, args.value)

    connection.commit()
    connection.close()


