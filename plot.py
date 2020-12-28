#coding:utf-8
import matplotlib.pyplot as plt 
import numpy as np
import code
def timePlot():
    def getData(s):
        X, Y = [], []
        lines = s.split('\n')
        for line in lines:
            line=line.strip()
            if line:
                data = line.strip()
                part = data.split(' ')
                x = int(part[0])
                y = float(part[1])
                X.append(x)
                Y.append(y)
        return X, Y
    t1='''
100000 21.68
200000 50.095
300000 75.683
400000 94.585
500000 137.244
600000 162.083
700000 194.541
800000 225.717
900000 254.506
1000000 288.489
    '''
    t2='''
100000 25.797
200000 52.448
300000 84.24
400000 120.81
500000 150.024
600000 185.53
700000 242.918
800000 266.128
900000 284.752
1000000 312.895
'''
    t3='''
100000 20.215
200000 52.839
300000 75.305
400000 107.386
500000 138.363
600000 171.215
700000 216.032
800000 208.4
900000 228.251
1000000 253.592
'''
    t4='''
100000 28.555
200000 63.482
300000 95.138
400000 112.219
500000 137.729
600000 165.777
700000 194.256
800000 222.759
900000 252.33
1000000 285.326
'''
    X, Y = getData(t1)
    plt.plot(X, Y, label='AS6057', marker='o')
    X, Y = getData(t2)
    plt.plot(X, Y, label='AS8881', marker='o')
    X, Y = getData(t3)
    plt.plot(X, Y, label='AS9146', marker='o')
    X, Y = getData(t4)
    plt.plot(X, Y, label='All', marker='o')
    plt.grid()
    plt.legend() # 显示图例
    plt.xlabel('Training size')
    plt.ylabel('Training time(s)')
    plt.show()

def asnDist():
    filename='/home/tony/datas/2019-05-26/Exp/AS/ASN_statistics.txt'
    data=open(filename).read()
    lines=data.split('\n')
    lines=lines[1:-4]
    counts = []
    for line in lines:
        count = int(line.strip().split(' ')[-2])
        counts.append(count)
    total = (float)(sum(counts))
    percent = []
    for i in xrange(len(counts)):
        v = counts[i] / total
        if i != 0:
            v += percent[i - 1]
        percent.append(v) 
    X=[i + 1 for i in xrange(len(counts))]
    X=np.log10(X)
    plt.figure()
    plt.grid()
    plt.xlabel('Number of ASNs(log10)')
    plt.ylabel('Total percentage of addresses(%)')
    plt.plot(X, percent)
    plt.show()
    #code.interact(banner = "", local = dict(globals(), **locals()))
asnDist()