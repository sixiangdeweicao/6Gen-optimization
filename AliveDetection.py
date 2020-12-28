#coding:utf-8
'''
    sudo python AliveDetection.py --input=[input.txt] --filename=[alive.txt] --dir=[dirname] --IPv6=[IP]
'''
import argparse, json, os, time, subprocess
if __name__=='__main__':
    parse=argparse.ArgumentParser()
    parse.add_argument('--filename', type=str, help='alive filename(absolute)')
    parse.add_argument('--input','-i',type=str,help='input IPv6 addresses. # to comment \\n to split')
    parse.add_argument('--dir',type=str,help='output directory name')
    parse.add_argument('--IPv6',type=str,help='local IPv6 address')
    args=parse.parse_args()

    if args.input != None and args.dir != None and args.filename != None and args.IPv6 != None:
        directory = args.dir
        if not os.path.exists(directory):
            os.mkdir(directory)
        zmapfilename = '{}/zmap_{}'.format(directory, args.input.split('/')[-1])
        command = 'sudo zmap --ipv6-target-file={} --ipv6-source-ip={} -M icmp6_echoscan -f saddr,daddr,ipid,ttl,timestamp_str -O json -o {}'.format(args.input, args.IPv6, zmapfilename)
        print('zmap scanning {}, store result in {}'.format(args.input, zmapfilename))
        t0 = time.time()
        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        returncode = p.poll()
        while returncode is None:
            line = p.stdout.readline()
            returncode = p.poll()
            line = line.strip()
            #print(line)
        print('zmap_scanning use {} seconds'.format(time.time() - t0))
        count = 0
        resultfilename = args.filename
        with open(resultfilename, 'w') as f:
            for line in open(zmapfilename, 'r'):
                responsive_IP=json.loads(line)['saddr']
                f.write(responsive_IP + '\n')
                count += 1
        print('find {} alive IPs writing to {} file'.format(count, resultfilename))