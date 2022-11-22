import brownie
from brownie import Contract, accounts, chain, ZERO_ADDRESS
import pytest

def test_valid_token(
    token1, token2, token1_whale, bribe, gov, user,
    token2_whale, gauge1, gauge2, gauge_controller, voter1, voter2
):
    # This is an address with no code
    empty_token = '0x55c85b7d1d4Ca6689Ec826390a9eb0e21160EB04'
    with brownie.reverts():
        tx = bribe.add_reward_amount(gauge1, empty_token, 100e18, {'from': gov})

    # This is ZERO_ADDRESS
    with brownie.reverts():
        tx = bribe.add_reward_amount(gauge1, ZERO_ADDRESS, 100e18, {'from': gov})

    # This is a valid contract, but doesn't have ERC20 interface
    non_token = '0x8888881B7Bf2A28686e25Bf82F8608c36A11F030'
    with brownie.reverts():
        tx = bribe.add_reward_amount(gauge1, non_token, 100e18, {'from': gov})