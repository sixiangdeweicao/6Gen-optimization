#!/bin/bash
# 对比1位划分和4位划分的效果
# 进行活跃探测
# 时间和命中率
funSetEnv() {
    # RawAddress Dirname nonaliasedprefix aliasedprefix ipv6
    RawAddress=$1  # 初始地址
    Dirname=$2 # 结果文件夹
    NonAliasedPrefix=$3  # 非别名前缀文件
    AliasedPrefix=$4 # 别名前缀文件
    LocalIP=$5 # IPv6地址
    APDDir="$2/APD" # APD 结果文件夹
    AS_AliveDir="$2/Alive" # 活跃结果文件夹
    ZmapDir="$2/Zmap"
    NonAliasedRawAddress="$APDDir/non-aliased.txt"  # 非别名地址
    AliasedRawAddress="$APDDir/aliased.txt"   # 别名地址
    AliveRawAddress="$AS_AliveDir/alive.txt"
    Budgets="100000000"
    sudo mkdir -p $Dirname $APDDir $ZmapDir $AS_AliveDir
}
funCheckEnv() {
    echo $RawAddress
    echo $Dirname
}
funAddr2Hex() {
    # $1 raw address -> $2 hex address
    sudo cat $1 | sudo ipv6-addr2hex | sudo tee $2 > /dev/null
}
funHex2Addr() {
    # $1 hex address -> $2 raw address
    sudo cat $1 | sudo ipv6-hex2addr | sudo tee $2 > /dev/null
}
funAPD() {
    # 去别名前缀
    echo '[APD]'
    time sudo python aliases-lpm.py -i $RawAddress -n $NonAliasedPrefix -a $AliasedPrefix --non-aliased-result $NonAliasedRawAddress --aliased-result $AliasedRawAddress
}
funAliveDetection() {
    # 活跃性
    echo '[AliveDetect]'
    sudo python AliveDetection.py --input=$NonAliasedRawAddress --dir=$AS_AliveDir --filename=$AliveRawAddress --IPv6=$LocalIP > /dev/null
}
funASSplit() {
    # AS 划分
    echo '[ASSplit]'
    sudo python AS_split.py --src $1 --dst $2 --dat ipasn.dat > /dev/null
    sudo python AS_split.py -analyze --min 2 --dst $2 > /dev/null
    sudo python AS_split.py -split --dst $2 --mode AS --value 3 > /dev/null # 生成3个AS文件
}
funFormatIP() {
    # AS文件夹下的地址文件格式化成32位16进制地址
    for filename in `ls $1/AS[0-9]*.txt`;do
        echo "formatting $filename..."
        funAddr2Hex "$filename" "${filename/txt/hex}"
        sudo rm $filename
    done
}
funPreprocess() {
    # 预处理，处理到AS文件夹格式化
    echo '[Preprocess]'
    funAliveDetection
    funASSplit $AliveRawAddress $AS_AliveDir
    funFormatIP $AS_AliveDir
}
funScanning() {
    # 扫描地址, 训练地址
    sudo python UniqODedup.py -A $1 -B $2 -O "$1.dedup" > /dev/null
    funHex2Addr "$1.dedup" "$1.target"
    sudo rm -rf $1 "$1.dedup"
    sudo zmap -q -L $ZmapDir --ipv6-target-file="$1.target" --ipv6-source-ip=$LocalIP -M icmp6_echoscan -f saddr,daddr,ipid,ttl,timestamp_str -O json -o "$1.result"
}

doExperiment() {
    # 对指定文件进行训练与扫描
    echo "[do Experiment on $1]"
    filename_=$1
    subDirname_=$2
    sudo rm -rf $subDirname_
    sudo mkdir -p $subDirname_

    # my algorithm
    limit_filename="$subDirname_/limit_1"
    output_="$subDirname_/time.limit_1"
    (time sudo python patternMining.py --read $filename_ --write $limit_filename --budgets $Budgets --depth 1 --experience True --limit 1 >> "$subDirname_/patternMining.log.1") 2> >(sudo tee -a $output_ > /dev/null)
    filetarget_="$limit_filename.$Budgets"
    cat "$filetarget_.pattern" | ./expand | sudo tee $filetarget_ > /dev/null
    time funScanning $filetarget_ $filename_

    limit_filename="$subDirname_/limit_4"
    output_="$subDirname_/time.limit_4"
    (time sudo python patternMining.py --read $filename_ --write $limit_filename --budgets $Budgets --depth 1 --experience True --limit 4 >> "$subDirname_/patternMining.log.1") 2> >(sudo tee -a $output_ > /dev/null)
    filetarget_="$limit_filename.$Budgets"
    cat "$filetarget_.pattern" | ./expand | sudo tee $filetarget_ > /dev/null
    time funScanning $filetarget_ $filename_

}
Experiment_Compare() {
    # 使用不同limit比较时间、命中率
    for filename in `ls $AS_AliveDir/AS[0-9]*.hex`;do
        # 对每个AS进行实验
        SubDirname="${filename/.hex/}"
        doExperiment $filename $SubDirname
    done
}
if [ $# -eq 6 ]
then
    case ${@: -1} in
        0)
            funSetEnv $*
            funAPD
        ;;
        1)
            funSetEnv $*
            funPreprocess
        ;;
        2) 
            funSetEnv $*
            Experiment_Compare
        ;;
    esac
fi


exit 0