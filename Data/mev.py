'''
FBB_coinbase_transfer:
    Using flashbots api from 'https://blocks.flashbots.net/v1/blocks', add all the FBB coinbase transfers in a block.
    At the same time maintain a collection of FBB transactions to determine whether a transaction is an FBB transaction when calculating gas.

FBB_gas_fee:
    Scan each transaction in a block, if a transaction is FBB transaction, add the gas fee paid to the miner to result, excluding the saved fee and burnt fee after London Fork.

non_FBB_gas_fee:
    Scan each transaction in a block, if a transaction is NOT FBB transaction, add the gas fee paid to the miner to result, excluding the saved fee and burnt fee after London Fork.

static_reward:
    Static reward from mining a block.
    The value is 2 ether, static, after Constantinople Fork at block number 7280000.

uncle_incl_reward:
    Uncle including reward from add uncles to a block.
    The value is 1/32 ether per uncle included.
'''

import web3_api
import requests
import sys
import numpy as np
from hexbytes import HexBytes
import csv
import bisect
import seaborn as sns

block_start = 12710000
block_end = 13510000

london_fork = 12965000
block_interval = block_end - block_start
is_FBB_tx = set()
FBB_coinbase_transfer = [0] * block_interval
FBB_gas_fee = [0] * block_interval
non_FBB_gas_fee = [0] * block_interval
static_reward = [0] * block_interval
uncle_incl_reward = [0] * block_interval


def set_block_interval(start, end):
    global block_start, block_end, block_interval
    global is_FBB_tx, FBB_coinbase_transfer, FBB_gas_fee, non_FBB_gas_fee, static_reward, uncle_incl_reward
    block_start = start
    block_end = end
    block_interval = block_end - block_start
    is_FBB_tx = set()
    FBB_coinbase_transfer = [0] * block_interval
    FBB_gas_fee = [0] * block_interval
    non_FBB_gas_fee = [0] * block_interval
    static_reward = [0] * block_interval
    uncle_incl_reward = [0] * block_interval


def calc_FBB():
    print('begin calc_FBB')
    global is_FBB_tx, FBB_coinbase_transfer, FBB_gas_fee, non_FBB_gas_fee, static_reward, uncle_incl_reward
    header = {
        'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    }

    blockno = block_end
    while blockno > block_start:
        print('blockno =', blockno)
        url = 'https://blocks.flashbots.net/v1/blocks'
        content = requests.get(url,
                               params={
                                   'before': str(blockno),
                                   'limit': '4'
                               }).text
        true = True
        false = False
        null = None
        mp = eval(content)
        if mp['blocks'] == []: break
        for block in mp['blocks']:
            #modified because Flashbots API changes
            thisblockno = block['block_number']
            if thisblockno < block_start: continue
            blockno = min(blockno, thisblockno)
            FBB_coinbase_transfer[thisblockno - block_start] = int(
                block['coinbase_transfers'])
            FBB_gas_fee[thisblockno - block_start] = int(
                block['miner_reward']) - int(block['coinbase_transfers'])
            for tx in block['transactions']:
                txhash = HexBytes(tx['transaction_hash'])
                is_FBB_tx.add(txhash)
    print('end calc_FBB')


def calc_basic():
    print('begin calc_basic')
    global is_FBB_tx, FBB_coinbase_transfer, FBB_gas_fee, non_FBB_gas_fee, static_reward, uncle_incl_reward
    for blockno in range(block_start, block_end):
        print('blockno =', blockno)
        block_info = web3_api.get_block_info(blockno)

        if blockno < 7280000:
            assert (
                0
            )  #Constantinople fork, changing the static reward from 3 eth to 2 eth
        static_reward[blockno - block_start] = 2 * 10**18
        uncle_incl_reward[blockno - block_start] = len(
            block_info['uncles']) * 625 * 10**14

        basefee = 0
        if 'baseFeePerGas' in block_info:
            if type(block_info['baseFeePerGas']) == str:
                basefee = int(block_info['baseFeePerGas'], 16)
            elif type(block_info['baseFeePerGas']) == int:
                basefee = block_info['baseFeePerGas']
        sum = 0
        FBB_sum = 0
        for tx in block_info['transactions']:
            txhash = HexBytes(tx.hash)
            txtype = HexBytes(tx['type'])
            recepit = web3_api.get_tx_receipt(txhash)
            tx_gasfee = 0
            if txtype == HexBytes('0x0') or txtype == HexBytes('0x1'):
                assert (type(tx['gasPrice']) == int)
                assert (type(recepit['gasUsed']) == int)
                tx_gasfee = (tx['gasPrice'] - basefee) * recepit['gasUsed']
            elif txtype == HexBytes('0x2'):
                maxPriorityFeePerGas = tx['maxPriorityFeePerGas']
                if type(maxPriorityFeePerGas) == str:
                    maxPriorityFeePerGas = int(maxPriorityFeePerGas, 16)
                maxFeePerGas = tx['maxFeePerGas']
                if type(maxFeePerGas) == str:
                    maxFeePerGas = int(maxFeePerGas, 16)
                tx_gasfee = min(maxPriorityFeePerGas,
                                maxFeePerGas - basefee) * recepit['gasUsed']
            else:
                print('txtype =', txtype)
                print('txhash =', txhash.hex())
                print(tx)
                assert (0)
            sum += tx_gasfee
            FBB_sum += tx_gasfee if txhash in is_FBB_tx else 0

        #assert(FBB_sum == FBB_gas_fee[blockno-block_start]) usually is, but for miners tx, flashbots remove the gas from calculating
        FBB_gas_fee[blockno - block_start] = FBB_sum
        non_FBB_gas_fee[blockno - block_start] = sum - FBB_sum
    print('end calc_basic')


def write_list(li: list, path):
    f = open(path, 'w')
    f.write(str(li))
    f.close()


def read_list(path):
    f = open(path, 'r')
    s = f.read()
    return list(map(int, s[1:len(s) - 1].split(',')))


def MEVdata_to_csv(stepsize: int):
    writer = csv.writer(open('./MEVfig/MEVdata.csv', 'w', newline=''))
    writer.writerow(('block_number', 'FBB_coinbase_transfer', 'FBB_gas_fee',
                     'non_FBB_gas_fee', 'static_reward', 'uncle_incl_reward'))
    for start in range(block_start, block_end, stepsize):
        print(start)
        end = min(start + stepsize, block_end)
        file_prefix = './MEVdata/[%d,%d)' % (start, end)
        FBB_coinbase_transfer = read_list(file_prefix +
                                          'FBB_coinbase_transfer.txt')
        FBB_gas_fee = read_list(file_prefix + 'FBB_gas_fee.txt')
        non_FBB_gas_fee = read_list(file_prefix + 'non_FBB_gas_fee.txt')
        static_reward = read_list(file_prefix + 'static_reward.txt')
        uncle_incl_reward = read_list(file_prefix + 'uncle_incl_reward.txt')
        for blockno in range(start, end):
            #if blockno<12865000 or blockno>=13135000: continue
            id = blockno - start
            writer.writerow((blockno, FBB_coinbase_transfer[id],
                             FBB_gas_fee[id], non_FBB_gas_fee[id],
                             static_reward[id], uncle_incl_reward[id]))


def csv_to_img(bunch_size=10000):
    import matplotlib.pyplot as plt
    bar_cnt = (block_interval - 1) // bunch_size + 1
    FBB_coinbase_transfer = [0] * bar_cnt
    FBB_gas_fee = [0] * bar_cnt
    non_FBB_gas_fee = [0] * bar_cnt
    static_reward = [0] * bar_cnt
    uncle_incl_reward = [0] * bar_cnt
    x_before = []
    x_after = []
    FBB_before = []
    FBB_after = []
    non_before = []
    non_after = []
    ab_before = 0
    ab_after = 0
    reader = csv.reader(open('./MEVfig/MEVdata.csv'))
    istitle = True
    for row in reader:
        if istitle:
            istitle = False
            continue
        blockno = int(row[0])
        if blockno < block_start or blockno >= block_end: continue
        id = (blockno - block_start) // bunch_size
        FBB_coinbase_transfer[id] += float(row[1]) / 10**18 / bunch_size
        FBB_gas_fee[id] += float(row[2]) / 10**18 / bunch_size
        non_FBB_gas_fee[id] += float(row[3]) / 10**18 / bunch_size
        static_reward[id] += float(row[4]) / 10**18 / bunch_size
        uncle_incl_reward[id] += float(row[5]) / 10**18 / bunch_size
        all = (float(row[1]) + float(row[2]) + float(row[3]) + 0 +
               float(row[5])) / 10**18
        part_FBB = (float(row[1]) + float(row[2])) / 10**18
        part_non = (float(row[3]) + 0 + float(row[5])) / 10**18
        if part_FBB < 1e-9:
            #all = 3
            if blockno < london_fork:
                ab_before += 1
            else:
                ab_after += 1
        if blockno < london_fork:
            x_before.append(all)
            FBB_before.append(part_FBB)
            non_before.append(part_non)
        else:
            x_after.append(all)
            FBB_after.append(part_FBB)
            non_after.append(part_non)

    print(ab_before / len(x_before), np.var(FBB_before))
    print(ab_after / len(x_after), np.var(FBB_after))

    fontsize = 18

    def plt_init(size=18):
        #fig,ax=plt.subplots()
        plt.cla()
        plt.xticks(fontsize=size)
        plt.yticks(fontsize=size)
        #plt.xlabel(fontsize=size)
        #plt.ylabel(fontsize=size)
        #plt.legend(fontsize=size)

    plt_init()
    plt.xlabel("value (Ether)", fontsize=fontsize)
    plt.ylabel("density", fontsize=fontsize)
    plt.xlim(0, 2)
    plt.xticks([0., .5, 1., 1.5, 2.])
    fig = sns.histplot(np.array(x_before),
                       stat='density',
                       color='#1f77b4',
                       bins=100,
                       label='pre London Hardfork',
                       binrange=(0, 2),
                       edgecolor='none')
    #fig.legend(loc='upper center', ncol=2)
    fig = sns.histplot(np.array(x_after),
                       stat='density',
                       color='#ff7f0e',
                       bins=100,
                       label='post London Hardfork',
                       binrange=(0, 2),
                       edgecolor='none')
    fig.legend(loc='upper center', ncol=1, fontsize=fontsize)
    plt.gcf().subplots_adjust(left=.12, top=.97, bottom=0.13)
    plt.gcf().set_size_inches(12, 4.8)
    plt.savefig('./MEVfig/dist.pdf')
    plt.gcf().set_size_inches(6.4, 4.8)

    plt_init()
    plt.xlabel("value (Ether)", fontsize=fontsize)
    plt.ylabel("density", fontsize=fontsize)
    plt.xlim(0, 0.4)
    plt.xticks([0., .1, .2, .3, .4])
    plt.ylim(0, 40)
    fig = sns.histplot(np.array(FBB_before),
                       stat='density',
                       color='#1f77b4',
                       bins=100,
                       label='pre London Hardfork',
                       binrange=(0, .4),
                       edgecolor='none')
    #fig.legend(loc='upper center', ncol=2)
    fig = sns.histplot(np.array(FBB_after),
                       stat='density',
                       color='#ff7f0e',
                       bins=100,
                       label='post London Hardfork',
                       binrange=(0, .4),
                       edgecolor='none')
    fig.legend(loc='upper center', ncol=1, fontsize=fontsize)
    plt.gcf().subplots_adjust(left=.15, top=.97, bottom=0.13)
    plt.savefig('./MEVfig/dist_FBB.pdf')

    plt_init()
    plt.xlabel("value (Ether)", fontsize=fontsize)
    plt.ylabel("density", fontsize=fontsize)
    plt.xlim(0, 2)
    plt.xticks([0., .5, 1., 1.5, 2.])
    fig = sns.histplot(np.array(non_before),
                       stat='density',
                       color='#1f77b4',
                       bins=100,
                       label='pre London Hardfork',
                       binrange=(0, 2),
                       edgecolor='none')
    #fig.legend(loc='upper center', ncol=2)
    fig = sns.histplot(np.array(non_after),
                       stat='density',
                       color='#ff7f0e',
                       bins=100,
                       label='post London Hardfork',
                       binrange=(0, 2),
                       edgecolor='none')
    fig.legend(loc='upper center', ncol=1, fontsize=fontsize)
    plt.gcf().subplots_adjust(left=.15, top=.97, bottom=0.13)
    plt.savefig('./MEVfig/dist_non.pdf')

    labels = [blockno for blockno in range(block_start, block_end, bunch_size)]
    ticks = [block_start, london_fork, block_end
             ] if london_fork >= block_start and london_fork < block_end else [
                 block_start, block_end
             ]
    col = ['#e0ddde', '#bebcba', '#fa74a7', '#bfe2fe', '#9dcbff']

    print('begin paint whole')
    plt_init()
    fig, ax = plt.subplots()
    plt.xlabel('block number', fontsize=fontsize)
    plt.ylabel('value (Ether)', fontsize=fontsize)
    #ax.set_title('Source of MEV')
    plt.xticks(ticks, fontsize=fontsize)
    plt.yticks(fontsize=fontsize)
    plt.xlim((block_start, block_end))
    ax.get_xaxis().get_major_formatter().set_scientific(False)
    bottom = [0] * bar_cnt
    width = bunch_size
    ax.bar(labels,
           static_reward,
           bottom=bottom,
           width=width,
           label='static reward',
           align='edge',
           color=col[0])
    for i in range(len(bottom)):
        bottom[i] += static_reward[i]
    ax.bar(labels,
           uncle_incl_reward,
           bottom=bottom,
           width=width,
           label='uncle inclusion reward',
           align='edge',
           color=col[1])
    for i in range(len(bottom)):
        bottom[i] += uncle_incl_reward[i]
    ax.bar(labels,
           non_FBB_gas_fee,
           bottom=bottom,
           width=width,
           label='non-FBB gas fee',
           align='edge',
           color=col[2])
    for i in range(len(bottom)):
        bottom[i] += non_FBB_gas_fee[i]
    ax.bar(labels,
           FBB_gas_fee,
           bottom=bottom,
           width=width,
           label='FBB gas fee',
           align='edge',
           color=col[3])
    for i in range(len(bottom)):
        bottom[i] += FBB_gas_fee[i]
    ax.bar(labels,
           FBB_coinbase_transfer,
           bottom=bottom,
           width=width,
           label='FBB coinbase transfer',
           align='edge',
           color=col[4])
    for i in range(len(bottom)):
        bottom[i] += FBB_coinbase_transfer[i]
    ax.legend(loc='lower center', ncol=1, fontsize=fontsize)
    plt.gcf().subplots_adjust(left=.15, top=.97, bottom=0.13)
    plt.savefig('./MEVfig/whole.pdf')
    print('end paint whole')

    print('begin paint flashbots')
    plt_init()
    fig, ax = plt.subplots()
    plt.xlabel('block number', fontsize=fontsize)
    plt.ylabel('value (Ether)', fontsize=fontsize)
    #ax.set_title('MEV from Flashbots')
    plt.xticks(ticks, fontsize=fontsize)
    plt.yticks(fontsize=fontsize)
    plt.xlim((block_start, block_end))
    ax.get_xaxis().get_major_formatter().set_scientific(False)
    bottom = [0] * bar_cnt
    width = bunch_size
    ax.bar(labels,
           FBB_gas_fee,
           bottom=bottom,
           width=width,
           label='FBB gas fee',
           align='edge',
           color=col[3])
    for i in range(len(bottom)):
        bottom[i] += FBB_gas_fee[i]
    ax.bar(labels,
           FBB_coinbase_transfer,
           bottom=bottom,
           width=width,
           label='FBB coinbase transfer',
           align='edge',
           color=col[4])
    for i in range(len(bottom)):
        bottom[i] += FBB_coinbase_transfer[i]
    ax.legend(loc='upper center', ncol=1, fontsize=fontsize)
    plt.gcf().subplots_adjust(left=.15, top=.97, bottom=0.13)
    plt.savefig('./MEVfig/flashbots.pdf')
    print('end paint flashbots')

    print('begin paint ratio(flashbots-all)')
    plt_init()
    fig, ax = plt.subplots()
    plt.xlabel('block number', fontsize=fontsize)
    plt.ylabel('ratio', fontsize=fontsize)
    #ax.set_title('Ratio of MEV from Flashbots to total MEV')
    plt.xticks(ticks, fontsize=fontsize)
    plt.yticks(fontsize=fontsize)
    plt.xlim((block_start, block_end))
    ax.get_xaxis().get_major_formatter().set_scientific(False)
    ratio_FBB_gasfee = [0] * bar_cnt
    ratio_FBB_coinbase_transfer = [0] * bar_cnt
    width = bunch_size
    for i in range(bar_cnt):
        all = static_reward[i] + uncle_incl_reward[i] + non_FBB_gas_fee[
            i] + FBB_gas_fee[i] + FBB_coinbase_transfer[i]
        ratio_FBB_gasfee[i] = FBB_gas_fee[i] / all
        ratio_FBB_coinbase_transfer[i] = FBB_coinbase_transfer[i] / all
    bottom = [0] * bar_cnt
    width = bunch_size
    ax.bar(labels,
           ratio_FBB_gasfee,
           bottom=bottom,
           width=width,
           label='FBB gas fee',
           align='edge',
           color=col[3])
    for i in range(len(bottom)):
        bottom[i] += ratio_FBB_gasfee[i]
    ax.bar(labels,
           ratio_FBB_coinbase_transfer,
           bottom=bottom,
           width=width,
           label='FBB coinbase transfer',
           align='edge',
           color=col[4])
    for i in range(len(bottom)):
        bottom[i] += ratio_FBB_coinbase_transfer[i]
    ax.legend(loc='upper center', ncol=1, fontsize=fontsize)
    plt.gcf().subplots_adjust(left=.15, top=.97, bottom=0.13)
    plt.savefig('./MEVfig/ratio_all.pdf')
    print('end paint ratio(flashbots-all)')

    print('begin paint ratio(flashbots-nonstatic)')
    plt_init()
    fig, ax = plt.subplots()
    plt.xlabel('block number', fontsize=fontsize)
    plt.ylabel('ratio', fontsize=fontsize)
    #ax.set_title('Ratio of MEV from Flashbots to the non-static MEV')
    plt.xticks(ticks, fontsize=fontsize)
    plt.yticks(fontsize=fontsize)
    plt.xlim((block_start, block_end))
    ax.get_xaxis().get_major_formatter().set_scientific(False)
    ratio_FBB_gasfee = [0] * bar_cnt
    ratio_FBB_coinbase_transfer = [0] * bar_cnt
    width = bunch_size
    for i in range(bar_cnt):
        all = uncle_incl_reward[i] + non_FBB_gas_fee[i] + FBB_gas_fee[
            i] + FBB_coinbase_transfer[i]
        ratio_FBB_gasfee[i] = FBB_gas_fee[i] / all
        ratio_FBB_coinbase_transfer[i] = FBB_coinbase_transfer[i] / all
    bottom = [0] * bar_cnt
    width = bunch_size
    ax.bar(labels,
           ratio_FBB_gasfee,
           bottom=bottom,
           width=width,
           label='FBB gas fee',
           align='edge',
           color=col[3])
    for i in range(len(bottom)):
        bottom[i] += ratio_FBB_gasfee[i]
    ax.bar(labels,
           ratio_FBB_coinbase_transfer,
           bottom=bottom,
           width=width,
           label='FBB coinbase transfer',
           align='edge',
           color=col[4])
    for i in range(len(bottom)):
        bottom[i] += ratio_FBB_coinbase_transfer[i]
    ax.legend(loc='upper center', ncol=1, fontsize=fontsize)
    plt.gcf().subplots_adjust(left=.15, top=.97, bottom=0.13)
    plt.savefig('./MEVfig/ratio_nonstatic.pdf')
    print('end paint ratio(flashbots-nonstatic)')


def csv_distr_test(bunch_size=1):
    from scipy import stats
    bar_cnt = (block_interval - 1) // bunch_size + 1
    FBB_coinbase_transfer = [0] * bar_cnt
    FBB_gas_fee = [0] * bar_cnt
    non_FBB_gas_fee = [0] * bar_cnt
    static_reward = [0] * bar_cnt
    uncle_incl_reward = [0] * bar_cnt
    reader = csv.reader(open('./MEVfig/MEVdata.csv'))
    istitle = True
    for row in reader:
        if istitle:
            istitle = False
            continue
        blockno = int(row[0])
        if blockno < block_start or blockno >= block_end: continue
        id = (blockno - block_start) // bunch_size
        FBB_coinbase_transfer[id] += float(row[1]) / 10**18 / bunch_size
        FBB_gas_fee[id] += float(row[2]) / 10**18 / bunch_size
        non_FBB_gas_fee[id] += float(row[3]) / 10**18 / bunch_size
        static_reward[id] += float(row[4]) / 10**18 / bunch_size
        uncle_incl_reward[id] += float(row[5]) / 10**18 / bunch_size

    x = [0] * bar_cnt
    for i in range(bar_cnt):
        x[i] = FBB_gas_fee[i] + FBB_coinbase_transfer[i]

    x = x[0:10000]

    #import matplotlib.pyplot as plt
    #import seaborn
    #seaborn.kdeplot(x)
    #plt.show()

    res = stats.kstest(x, "gamma", stats.gamma.fit(x))
    print(res.pvalue)


if __name__ == '__main__':
    #f=open('tmp.txt','w')
    #print(web3_api.get_block_info(8364113,detail=False),file=f)
    #txhash = HexBytes('0x1c1281d2c858a2afcb50bc1df66a0d55aae692a5506ef66b3d4083c64b50f54d')
    #print(web3_api.get_tx_info(txhash),file =f)
    if len(sys.argv) == 1:
        print('Need at least one option: --data / --csv / --img')
        exit(0)
    elif len(sys.argv) == 4:
        set_block_interval(int(sys.argv[2]), int(sys.argv[3]))
    elif len(sys.argv) != 2:
        print('need 0 or 2 arguments [start,end)')
        exit(0)

    option = sys.argv[1]
    if option == '--data':
        calc_FBB()
        calc_basic()

        file_prefix = './MEVdata/[%d,%d)' % (block_start, block_end)
        write_list(FBB_coinbase_transfer,
                   file_prefix + 'FBB_coinbase_transfer.txt')
        write_list(FBB_gas_fee, file_prefix + 'FBB_gas_fee.txt')
        write_list(non_FBB_gas_fee, file_prefix + 'non_FBB_gas_fee.txt')
        write_list(static_reward, file_prefix + 'static_reward.txt')
        write_list(uncle_incl_reward, file_prefix + 'uncle_incl_reward.txt')
    elif option == '--csv':
        MEVdata_to_csv(20000)
    elif option == '--img':
        csv_to_img()
    elif option == '--test':
        csv_distr_test()
    else:
        print('unknown option')
        exit(0)