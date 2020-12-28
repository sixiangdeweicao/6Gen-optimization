#coding:utf-8
'''
    sudo python zmapconvert.py --input [input.txt] --output [output.txt]
'''
import argparse, json, os, time
if __name__=='__main__':
    parse=argparse.ArgumentParser()
    parse.add_argument('--output', type=str, help='alive filename(relative)')
    parse.add_argument('--input','-i',type=str,help='input IPv6 addresses. # to comment \\n to split')
    parse.add_argument('--csv',action='store_true',help='csv mode')
    args=parse.parse_args()
    with open(args.output, 'w') as f:
        if args.csv:
            print('csv mode:')
            infile = open(args.input)
            infile.readline()
            while True:
                line = infile.readline()
                if line:
                    responsive_IP=line.split(',')[0]
                    f.write(responsive_IP + '\n')
                else:
                    infile.close()
                    break
        else:
            for line in open(args.input, 'r'):
                responsive_IP=json.loads(line)['saddr']
                f.write(responsive_IP + '\n')
        