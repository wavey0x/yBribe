import brownie
from brownie import Contract, accounts, chain
import pytest

def test_fees(
    token1, token2, token1_whale, bribe, gov, user,
    token2_whale, gauge1, gauge2, gauge_controller, voter1, voter2
):

    bribe.add_to_blacklist(voter2, {'from': gov}) # YEARN
    WEEK = 86400 * 7
    period = int(chain.time() / WEEK) * WEEK

    # Add some bribes
    token1.approve(bribe, 2**256-1, {'from': token1_whale})
    token2.approve(bribe, 2**256-1, {'from': token2_whale})
    before1 = bribe.claimable(voter1, gauge1, token1)
    before2 = bribe.claimable(voter1, gauge1, token1)
    amt = 2_000e18
    recipient = bribe.fee_recipient()
    before_bal = token1.balanceOf(recipient)
    # Fee is taken on Add
    tx = bribe.add_reward_amount(gauge1, token1, amt, {'from': token1_whale})
    if bribe.fee_percent() > 0:
        fee_amt = tx.events['RewardAdded']['fee']
        assert token1.balanceOf(recipient) > before_bal
        assert token1.balanceOf(recipient) == before_bal + fee_amt
        assert fee_amt == bribe.fee_percent() / 10_000 * amt


    # Test adjusting fee
    with brownie.reverts():
        bribe.set_fee_percent(5_000,{'from':gov})
    with brownie.reverts():
        bribe.set_fee_percent(5_000,{'from':token2_whale})
    bribe.set_fee_percent(250,{'from':gov})
    # Test adjusting recipient
    with brownie.reverts():
        bribe.set_fee_recipient(gov,{'from':recipient})
    bribe.set_fee_recipient(gov,{'from':gov})

    recipient = bribe.fee_recipient()
    before_bal = token1.balanceOf(recipient)
    # Fee is taken on add_reward_amount
    tx = bribe.add_reward_amount(gauge1, token1, amt, {'from': token1_whale})
    fee_amt = tx.events['RewardAdded']['fee']
    assert token1.balanceOf(recipient) > before_bal
    assert token1.balanceOf(recipient) == before_bal + fee_amt
    assert fee_amt == bribe.fee_percent() / 10_000 * amt