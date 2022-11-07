import brownie
from brownie import Contract, accounts, chain, ZERO_ADDRESS
import pytest
from utils import to_address

def test_schdule_bribes(
    token1, token2, token1_whale, bribe, user,
    token2_whale, gauge1, gauge2, gauge_controller, voter1, voter2
):

    WEEK = 86400 * 7
    period = int(chain.time() / WEEK) * WEEK

    token1.approve(bribe, 2**256-1, {'from': token1_whale})
    token2.approve(bribe, 2**256-1, {'from': token2_whale})

    before1 = bribe.claimable(voter1, gauge1, token1)
    before2 = bribe.claimable(voter1, gauge1, token1)

    amount = 5_000e18
    n_periods = 5
    delay = 0
    tx2 = bribe.schedule_reward_amount(gauge1, token1, amount, n_periods, delay, {'from': token1_whale})
    
    balance = token1.balanceOf(bribe)
    fee = evm_div(int(amount) * int(n_periods) * int(bribe.fee_percent()), 10**18)
    assert balance == int(int(amount) * int(n_periods)) - int(fee)

    fee = amount * n_periods * bribe.fee_percent() / 1e18
    assert balance == int(amount) * int(n_periods) - int(fee)
    assert False

# EVM div semantics as a python function
def evm_div(x, y):
    if y == 0:
        return 0
    # NOTE: should be same as: round_towards_zero(Decimal(x)/Decimal(y))
    sign = -1 if (x * y) < 0 else 1
    return sign * (abs(x) // abs(y))  # adapted from py-evm