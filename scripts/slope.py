
import brownie
from brownie import Contract, accounts, chain, web3, yBribe
import pytest

def main():
    WEEK = 60 * 60 * 24 * 7
    gc = Contract('0x2F50D538606Fa9EDD2B11E2446BEb18C9D5846bB')
    ve = Contract('0x5f3b5DfEb7B28CDbD7FAba78963EE202a494e2A2')
    y = web3.ens.resolve('curve-voter.ychad.eth')
    convex = '0x989AEb4d175e16225E39E87d0D97A3360524AD80'
    u1 = '0x221c7c5a448c87F6834818f255d28e5A8124C4A1'
    u2 = '0x9c5083dd4838E120Dbeac44C052179692Aa5dAC5'
    period = int(chain.time() / WEEK) * WEEK
    peth_gauge = '0x3eE0bD06D004C25273339c5aD91e1443523DC2dF'
    spell_gauge = '0xd8b712d29381748dB89c36BCa0138d7c75866ddF'

    global_data = gc.points_weight(spell_gauge, period).dict()
    gauge_data = gc.points_sum(1,period).dict()
    u = gc.vote_user_slopes(y, spell_gauge).dict()
    g

    assert False
    # gc.vote_user_slopes(user, gauge).slope;

def next_time():
    WEEK = 60 * 60 * 24 * 7
    return int(chain.time() / WEEK) * WEEK + WEEK

from eth_utils import to_checksum_address
from web3 import Web3
from brownie import Contract, convert
import time
def test_create2():
    """Test the CREATE2 opcode Python.

    EIP-104
    https://github.com/ethereum/EIPs/blob/master/EIPS/eip-1014.md
    https://ethereum.stackexchange.com/questions/90895/how-to-implement-the-create2-in-python
    """
    address = '0x0e55AEF1B392b8491369091ad808E87feaa4AfAB'
    
    pre = '0xff'
    b_pre = bytes.fromhex(pre[2:])
    b_address = bytes.fromhex(address[2:])
    b_init_code = bytes.fromhex(yBribe.bytecode)
    keccak_b_init_code = Web3.keccak(b_init_code)
    
    
    found = False
    i = 0
    start = time.time()

    while not found:
        salt = convert.to_bytes(i, "bytes32")
        b_result = Web3.keccak(b_pre + b_address + salt + keccak_b_init_code)
        result_address = to_checksum_address(b_result[12:].hex())
        print(f'{result_address} {result_address[2:8].lower()} salt: {i}')
        if result_address[2:8].lower() == 'b71be5':
            found = True
            print('🎉🍾🥳🍻')
        i += 1
    end = time.time()
    print(f'Execution time: {end - start}s')