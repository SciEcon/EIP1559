import os
from hexbytes import HexBytes
import web3_api
import csv
import numpy as np
import sys
import copy

block_start = 12865000
block_end = 13135000
database={}
blockdetail={}
nevertx={}

def set_block_interval(start,end):
    global block_start,block_end
    block_start = start
    block_end  = end

def build_database(path="./compressed"):
    global database
    for root,dirs,files in os.walk(path):
        for name in files:
            print("begin uncompress "+name)
            f=open(os.path.join(root, name),'r')
            for line in f.readlines():
                (txhash,recv_time)=line.split()
                txhash=HexBytes(txhash)
                recv_time=float(recv_time)
                if (txhash not in database) or (recv_time < database[txhash]):
                    database[txhash]=recv_time
            print("end uncompress "+name)


def gen_nevertx(lim=10):
    global nevertx
    print('begin gen_nevertx')
    
    next_block_info = web3_api.get_block_info(block_start,detail=False)
    for blockno in range(block_start,block_end):
        print('init blockno =',blockno)
        block_info = next_block_info
        next_block_info = web3_api.get_block_info(blockno+1,detail=False)
        nxt=next_block_info['timestamp']

        li=[]
        for tx in block_info['transactions']:
            txhash=HexBytes(tx)
            if (txhash not in database) or (database[txhash]>nxt+lim):
                li.append(txhash)
        nevertx[blockno]=li

    print('end gen_nevertx')


def gen_blockdetail():
    global blockdetail
    print('begin gen_blockdetail')
    
    next_block_info = web3_api.get_block_info(block_start,detail=True)
    for blockno in range(block_start,block_end):
        print('init blockno =',blockno)
        block_info = next_block_info
        next_block_info = web3_api.get_block_info(blockno+1,detail=True)

        blockdetail[blockno]={}
        blockdetail[blockno]['gasUsed']=block_info['gasUsed']
        blockdetail[blockno]['gasLimit']=block_info['gasLimit']
        blockdetail[blockno]['txCount']=len(block_info['transactions'])
        blockdetail[blockno]['uncleCount']=len(block_info['uncles'])
        blockdetail[blockno]['nextTimestamp']=next_block_info['timestamp']
        nxt=next_block_info['timestamp']

        recv_time=[]
        legacy_recv_time=[]
        eip1559_recv_time=[]
        for tx in block_info['transactions']:
            txhash=HexBytes(tx['hash'])
            txtype=HexBytes(tx['type'])
            tim=float('inf') if txhash not in database else database[txhash]
            recv_time.append(tim)
            if txtype==HexBytes('0x0') or txtype==HexBytes('0x1'):
                legacy_recv_time.append(tim)
            elif txtype==HexBytes('0x2'):
                eip1559_recv_time.append(tim)
            else:
                assert(0)

        if False:
            blockdetail[blockno]['recv_time']=copy.deepcopy(recv_time)
        
        blockdetail[blockno]['txtype_all']={}
        blockdetail[blockno]['txtype_legacy']={}
        blockdetail[blockno]['txtype_eip1559']={}

        blockdetail[blockno]['txtype_all']['cnt']=len(recv_time)
        blockdetail[blockno]['txtype_all']['cntLate']=sum([(1. if t>nxt+1. else 0.) for t in recv_time])
        blockdetail[blockno]['txtype_all']['cntNever']=sum([(1. if t==float('inf') else 0.) for t in recv_time])
        
        blockdetail[blockno]['txtype_legacy']['cnt']=len(legacy_recv_time)
        blockdetail[blockno]['txtype_legacy']['cntLate']=sum([(1. if t>nxt+1. else 0.) for t in legacy_recv_time])
        blockdetail[blockno]['txtype_legacy']['cntNever']=sum([(1. if t==float('inf') else 0.) for t in legacy_recv_time])
        
        blockdetail[blockno]['txtype_eip1559']['cnt']=len(eip1559_recv_time)
        blockdetail[blockno]['txtype_eip1559']['cntLate']=sum([(1. if t>nxt+1. else 0.) for t in eip1559_recv_time])
        blockdetail[blockno]['txtype_eip1559']['cntNever']=sum([(1. if t==float('inf') else 0.) for t in eip1559_recv_time])
        
        recv_time.sort()
        legacy_recv_time.sort()
        eip1559_recv_time.sort()
        if len(recv_time)==0:
            recv_time.append(float(blockdetail[blockno]['nextTimestamp']))
        if len(legacy_recv_time)==0: 
            legacy_recv_time.append(float(blockdetail[blockno]['nextTimestamp']))
        if len(eip1559_recv_time)==0:
            eip1559_recv_time.append(float(blockdetail[blockno]['nextTimestamp']))
        
        blockdetail[blockno]['txtype_all']['recvtimeQuantile25']=recv_time[int(len(recv_time)*.25)]
        blockdetail[blockno]['txtype_all']['recvtimeQuantile50']=recv_time[int(len(recv_time)*.5)]
        blockdetail[blockno]['txtype_all']['recvtimeQuantile75']=recv_time[int(len(recv_time)*.75)]
        
        blockdetail[blockno]['txtype_legacy']['recvtimeQuantile25']=legacy_recv_time[int(len(legacy_recv_time)*.25)]
        blockdetail[blockno]['txtype_legacy']['recvtimeQuantile50']=legacy_recv_time[int(len(legacy_recv_time)*.5)]
        blockdetail[blockno]['txtype_legacy']['recvtimeQuantile75']=legacy_recv_time[int(len(legacy_recv_time)*.75)]
        
        blockdetail[blockno]['txtype_eip1559']['recvtimeQuantile25']=eip1559_recv_time[int(len(eip1559_recv_time)*.25)]
        blockdetail[blockno]['txtype_eip1559']['recvtimeQuantile50']=eip1559_recv_time[int(len(eip1559_recv_time)*.5)]
        blockdetail[blockno]['txtype_eip1559']['recvtimeQuantile75']=eip1559_recv_time[int(len(eip1559_recv_time)*.75)]
        
    print('end gen_blockdetail')

def blockdetail_to_waitingtime_csv():
    writer = csv.writer(open('./save/waitingtime_csv.csv','w',newline=''))
    writer.writerow(('block_number',\
                     'uncle_cnt',\
                     'txtype_all_cnt',\
                     'txtype_all_latetx_cnt',\
                     'txtype_all_nevertx_cnt',\
                     'txtype_all_waitingtimeQuantile75',\
                     'txtype_all_waitingtimeQuantile50',\
                     'txtype_all_waitingtimeQuantile25',\
                     'txtype_legacy_cnt',\
                     'txtype_legacy_latetx_cnt',\
                     'txtype_legacy_nevertx_cnt',\
                     'txtype_legacy_waitingtimeQuantile75',\
                     'txtype_legacy_waitingtimeQuantile50',\
                     'txtype_legacy_waitingtimeQuantile25',\
                     'txtype_eip1559_cnt',\
                     'txtype_eip1559_latetx_cnt',\
                     'txtype_eip1559_nevertx_cnt',\
                     'txtype_eip1559_waitingtimeQuantile75',\
                     'txtype_eip1559_waitingtimeQuantile50',\
                     'txtype_eip1559_waitingtimeQuantile25'))
    for blockno in range(block_start,block_end):
        data=blockdetail[blockno]
        nxt=data['nextTimestamp']
        writer.writerow((blockno,\
                         data['uncleCount'],\
                         data['txtype_all']['cnt'],\
                         data['txtype_all']['cntLate'],\
                         data['txtype_all']['cntNever'],\
                         nxt-data['txtype_all']['recvtimeQuantile25'],\
                         nxt-data['txtype_all']['recvtimeQuantile50'],\
                         nxt-data['txtype_all']['recvtimeQuantile75'],\
                         data['txtype_legacy']['cnt'],\
                         data['txtype_legacy']['cntLate'],\
                         data['txtype_legacy']['cntNever'],\
                         nxt-data['txtype_legacy']['recvtimeQuantile25'],\
                         nxt-data['txtype_legacy']['recvtimeQuantile50'],\
                         nxt-data['txtype_legacy']['recvtimeQuantile75'],\
                         data['txtype_eip1559']['cnt'],\
                         data['txtype_eip1559']['cntLate'],\
                         data['txtype_eip1559']['cntNever'],\
                         nxt-data['txtype_eip1559']['recvtimeQuantile25'],\
                         nxt-data['txtype_eip1559']['recvtimeQuantile50'],\
                         nxt-data['txtype_eip1559']['recvtimeQuantile75']))
        
if __name__=='__main__':
    if len(sys.argv)==1:
        print('Need at least one option: --data / --csv')
        exit(0)
    elif len(sys.argv)==4:
        set_block_interval(int(sys.argv[2]),int(sys.argv[3]))
    elif len(sys.argv)!=2:
        print('need 0 or 2 more arguments besides option [start,end)')
        exit(0)
    
    option = sys.argv[1]
    if option == '--data':
        build_database()
        gen_blockdetail()
        np.save('./save/blockdetail',blockdetail)
        #print(blockdetail)
    elif option == '--csv':
        blockdetail = np.load('./save/blockdetail.npy',allow_pickle=True).item()
        blockdetail_to_waitingtime_csv()
    elif option == '--nevertx':
        build_database()
        gen_nevertx()
        np.save('./save/nevertx',nevertx)
    else:
        print('unknown option')
        exit(0)