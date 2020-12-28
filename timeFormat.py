#coding:utf-8
# python timeFormat.py --input [filename]
import argparse
parse=argparse.ArgumentParser()
parse.add_argument('--input',type=str,help='input timefile')
args=parse.parse_args()
data=open(args.input).read()
lines=data.split('\n')
length=len(lines)
for i in range(0, length - 1, 5):
    count = int(lines[i])
    time = lines[i + 2].split('\t')[-1]
    values=time.split('m')
    minute, second=int(values[0]), float(values[1][:-1])
    second = 60 * minute + second
    print('{} {}'.format(count, second))
