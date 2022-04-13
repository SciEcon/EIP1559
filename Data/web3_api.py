from web3 import Web3
from hexbytes import HexBytes
w3 = Web3()


#tx_recepit = {}
def get_tx_receipt(txhash):
    assert(type(txhash)==HexBytes)
    #if (txhash in tx_recepit): return tx_recepit[txhash]
    recepit = w3.eth.getTransactionReceipt(txhash)
    #tx_recepit[txhash] = recepit
    return recepit


#block_info = {}
def get_block_info(blockno,detail=True):#note! something is not HexBytes
    #if blockno in block_info: return block_info[blockno]
    info = w3.eth.getBlock(blockno,detail)
    #block_info[blockno]=info
    return info

def get_tx_info(txhash):
    assert(type(txhash)==HexBytes)
    info = w3.eth.getTransaction(txhash)
    return info


def sha3(s:str):
    return Web3.sha3(text=s)