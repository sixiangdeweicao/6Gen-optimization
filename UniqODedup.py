#coding:utf-8
'''
    unique or dedup
    usage:
    python UniqODedup.py -U [file.txt] -O [output.txt]      file每行去重
    python UniqODedup.py -A [file.txt] -B [fileB.txt] -O [output.txt]  将fileA - fileB的输出到fileC中
    临时文件夹在output.txt的目录下
'''
import argparse, os, binascii, time
MEMORY_LIMIT=800*2**20
def unique(input_filename, output_filename):
    size_input=os.path.getsize(input_filename)
    if size_input < MEMORY_LIMIT:
        IP_set=set()
        t = time.time()
        for line in open(input_filename):
            if line and line[0]!='#':
                IP=line.strip()
                IP_set.add(IP)
        with open(output_filename,'w') as f:
            for IP in IP_set:
                f.write(IP+'\n')
        print('size {} use {} seconds'.format(size_input, time.time() - t))
        return
    output_dirname=os.path.dirname(os.path.abspath(output_filename))
    temp_dir=output_dirname+'/UniqODedup_TempDir'
    if not os.path.exists(temp_dir):
        os.mkdir(temp_dir)
    flist=[]
    for i in xrange(16):
        f=open(temp_dir+'/'+str(i),'w')
        flist.append(f)
    t=time.time()
    count = 0
    for line in open(input_filename):
        if line and line[0] != '#':
            IP=line.strip()
            index=binascii.crc32(IP)%16
            flist[index].write(IP+'\n')
            count += 1
    for f in flist:
        f.close()
    print('split {} IP use {} seconds'.format(count, time.time() - t))
    t=time.time()
    f=open(output_filename, 'w')
    for i in xrange(16):
        data=open(temp_dir+'/'+str(i)).read()
        IPs=data.split('\n')[:-1]
        for IP in set(IPs):
            f.write(IP+'\n')
    f.close()
    print('output use {} seconds'.format(time.time() - t))
    clean_command='rm -rf {}'.format(temp_dir)
    os.system(clean_command)

def dedup(A, B, C):
    size_A, size_B = os.path.getsize(A), os.path.getsize(B)
    if size_A <= MEMORY_LIMIT:
        print('A size < MEMORY:')
        A_IPs=set()
        for line in open(A):
            if line and line[0]!='#':
                IP=line.strip()
                A_IPs.add(IP)
        for line in open(B):
            if line and line[0]!='#':
                IP=line.strip()
                if IP in A_IPs:
                    A_IPs.remove(IP)
        with open(C,'w') as f:
            for IP in A_IPs:
                f.write(IP+'\n')
        return
    if size_A > MEMORY_LIMIT:
        t0=time.time()
        print('A size > MEMORY')
        output_dirname=os.path.dirname(os.path.abspath(C))
        temp_dir=output_dirname+'/UniqODedup_DedupDir'
        if not os.path.exists(temp_dir):
            os.mkdir(temp_dir)
        flist=[]
        for i in xrange(16):
            f=open(temp_dir+'/'+str(i),'w')
            flist.append(f)
        t=time.time()
        count = 0
        for line in open(A):
            if line and line[0] != '#':
                IP=line.strip()
                index=binascii.crc32(IP)%16
                flist[index].write(IP+'\n')
                count += 1
        for f in flist:
            f.close()
        print('split A {} IP use {} seconds'.format(count, time.time() - t))
        flist_B=[]
        t=time.time()
        count = 0
        for i in xrange(16):
            f=open(temp_dir+'/_'+str(i),'w')
            flist_B.append(f)
        for line in open(B):
            if line and line[0] != '#':
                IP=line.strip()
                index=binascii.crc32(IP)%16
                flist_B[index].write(IP+'\n')
                count += 1
        for f in flist_B:
            f.close()
        print('split B {} IP use {} seconds'.format(count, time.time() - t))
        with open(C, 'w') as f:
            for i in xrange(16):
                data=open(temp_dir+'/'+str(i)).read()
                IPs=set(data.split('\n')[:-1])
                for line in open(temp_dir+'/_'+str(i)):
                    if line and line[0] != '#':
                        IP=line.strip()
                        if IP in IPs:
                            IPs.remove(IP)
                for IP in IPs:
                    f.write(IP+'\n')
        print('output use {} seconds'.format(time.time() - t0))
        clean_command='rm -rf {}'.format(temp_dir)
        os.system(clean_command)
        return
            
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-U", type=str, help="file to execute unique action")
    parser.add_argument("-O", type=str, help="output filename")
    parser.add_argument("-A", type=str, help="A filename")
    parser.add_argument("-B", type=str, help="B filename")
    args = parser.parse_args()
    if args.U != None:
        unique(args.U, args.O)
    else:
        dedup(args.A, args.B, args.O)