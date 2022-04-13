import os
from hexbytes import HexBytes
import web3_api
import csv
import numpy as np
import sys
import copy

block_start = 12865000
block_end = 13135000
gasused = {}
sibling_cnt = {}
timestamp = {}
is_hotspot = {}
avggas_per = {}

def set_block_interval(start,end):
    global block_start,block_end
    block_start = start
    block_end  = end

def init():
    reader = csv.reader(open('./blockdata/gas_csv.csv','r'))
    istitle = True
    for row in reader:
        if istitle:
            istitle = False
            continue
        blockno = int(row[0])
        gas = int(row[1])
        gasused[blockno] = gas
    reader = csv.reader(open('./blockdata/sibling_csv.csv','r'))
    istitle = True
    for row in reader:
        if istitle:
            istitle = False
            continue
        blockno = int(row[0])
        cnt = int(row[1])
        sibling_cnt[blockno] = cnt
    reader = csv.reader(open('./blockdata/timestamp_csv.csv','r'))
    istitle = True
    for row in reader:
        if istitle:
            istitle = False
            continue
        blockno = int(row[0])
        ts = int(row[1])
        timestamp[blockno] = ts

def write_csv():
    writer = csv.writer(open('./spikedata/avggas.csv','w',newline=''))
    writer.writerow(('block_number','20 sec','30 sec','40 sec','60 sec','90 sec','120 sec'))
    for blockno in range(block_start,block_end):
        writer.writerow((blockno,avggas_per[20][blockno],avggas_per[30][blockno],avggas_per[40][blockno]\
                        ,avggas_per[60][blockno],avggas_per[90][blockno],avggas_per[120][blockno]))
        
def indicate_hotspots(period:int,gaspersec:int):
    for blockno in range(block_start,block_end):
        is_hotspot[blockno] = False
    for blockno in range(block_start,block_end):
        sum = -gasused[blockno]
        bk = blockno
        while (timestamp[bk]>timestamp[blockno]-period):
            bk -= 1
            sum += gasused[bk+1]

        is_hotspot[blockno]= (sum>=period*gaspersec)

def calc_avggas_per(period:int):
    for blockno in range(block_start,block_end):
        sum = -gasused[blockno]
        bk = blockno
        while (timestamp[bk]>timestamp[blockno]-period):
            bk -= 1
            sum += gasused[bk+1]
        sum /= period
        avggas_per[period][blockno]=sum

if __name__=='__main__':
    set_block_interval(12895000,13105000)
    #set_block_interval(13035000,13105000)
    init()

    gasused[12894999]=14763353;sibling_cnt[12894999]=0
    gasused[12894998]=14984748;sibling_cnt[12894998]=0
    gasused[12894997]=14980637;sibling_cnt[12894997]=0
    gasused[12894996]=14965180;sibling_cnt[12894996]=0
    gasused[12894995]=14952940;sibling_cnt[12894995]=0
    gasused[12894994]=14958059;sibling_cnt[12894994]=0
    gasused[12894993]=14966093;sibling_cnt[12894993]=0
    gasused[12894992]=14727000;sibling_cnt[12894992]=0
    gasused[12894991]=14960561;sibling_cnt[12894991]=0
    gasused[12894990]=14946131;sibling_cnt[12894990]=0
    gasused[12894989]=14976050;sibling_cnt[12894989]=0
    gasused[12894988]=14970445;sibling_cnt[12894988]=0
    gasused[12894987]=14979409;sibling_cnt[12894987]=0
    gasused[12894986]=14988665;sibling_cnt[12894986]=0
    gasused[12894985]=14717667;sibling_cnt[12894985]=0

    for period in (20,30,40,60,90,120):
        avggas_per[period]={}
        calc_avggas_per(period)
        print('period = ',period)
        for threshold in (1000000,1200000,1400000,1600000,1800000,2000000,2200000,2400000):
            cnt = 0
            for blockno in range(13035000,13105000):
                if avggas_per[period][blockno]>=threshold:
                    cnt += 1
            print('%.2f'%(cnt/70000*100,),end=' & ')
        print('')
    write_csv()
