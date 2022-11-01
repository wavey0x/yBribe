import brownie
from brownie import Contract, accounts, chain
import pytest
from utils import to_address

def test_operation(
    token1, token2, token1_whale, bribe, user,
    token2_whale, gauge1, gauge2, gauge_controller, voter1, voter2
):

    WEEK = 86400 * 7
    period = int(chain.time() / WEEK) * WEEK

    # Poke gauges
    bribe.claim_reward(gauge1, token1, {'from':user})
    bribe.claim_reward(gauge2, token2, {'from':user})

    token1.approve(bribe, 2**256-1, {'from': token1_whale})
    token2.approve(bribe, 2**256-1, {'from': token2_whale})

    before1 = bribe.claimable(voter1, gauge1, token1)
    before2 = bribe.claimable(voter1, gauge1, token1)
    bribe.add_reward_amount(gauge1, token1, 2_000e18, {'from': token1_whale})
    bribe.add_reward_amount(gauge2, token2, 5_000e18, {'from': token2_whale})
    after1 = bribe.claimable(voter1, gauge1, token1)
    after2 = bribe.claimable(voter2, gauge2, token2)
    # Ensure claimable amount doesn't change. 
    # This test verifies that user must wait until following week to claim newly added rewards
    assert before1 == after1
    assert before2 == after2

    chain.sleep(WEEK)
    chain.mine(1)
    gauge_controller.checkpoint({'from':voter1})
    gauge_controller.checkpoint_gauge(gauge1, {'from': voter1})
    gauge_controller.checkpoint_gauge(gauge2, {'from': voter2})

    # Here we hvae to poke the gauge/update the period
    tx = bribe.add_reward_amount(gauge1, token1, 1, {'from': token1_whale})
    tx = bribe.add_reward_amount(gauge2, token2, 1, {'from': token2_whale})
    
    v1 = gauge_controller.vote_user_slopes(voter1, gauge1).dict()
    v2 = gauge_controller.vote_user_slopes(voter2, gauge1).dict()
    print(v1)
    print(v2)
    if v1['power'] > 0:
        assert bribe.claimable(voter1, gauge1, token1) > after1
    else:
        assert bribe.claimable(voter1, gauge1, token1) == 0
    
    if v2['power'] > 0:
        assert bribe.claimable(voter2, gauge1, token1) > after2
    else:
        assert bribe.claimable(voter2, gauge1, token1) == 0

    # gauge_controller.vote_for_gauge_weights(gauge2, 0,{'from': voter1})
    # gauge_controller.vote_for_gauge_weights(gauge2, 0,{'from': voter2})

def test_claim_reward_for_many(
    token1, token2, token1_whale, bribe, gov, accounts, WEEK, user,
    token2_whale, gauge1, gauge2, gauge_controller, voter1, voter2
):
    token1.approve(bribe, 2**256-1, {'from': token1_whale})
    tx = bribe.add_reward_amount(gauge1, token1, 1_000_000e18, {'from': token1_whale})

    chain.sleep(WEEK)
    chain.mine(1)
    gauge_controller.checkpoint({'from':voter1})
    gauge_controller.checkpoint_gauge(gauge1, {'from': voter1})
    gauge_controller.checkpoint_gauge(gauge2, {'from': voter2})

    users = [voter1, voter2]
    gauges = [gauge1, gauge2]
    tokens = [token1, token2]
    bribe.claim_reward_for_many(users, gauges, tokens, {'from':user})

def test_delegate(
    token1, token2, token1_whale, bribe, gov, accounts, WEEK, user,
    token2_whale, gauge1, gauge2, gauge_controller, voter1, voter2
):
    token1.approve(bribe, 2**256-1, {'from': token1_whale})
    tx = bribe.add_reward_amount(gauge1, token1, 1_000_000e18, {'from': token1_whale})

    chain.sleep(WEEK)
    chain.mine(1)
    gauge_controller.checkpoint({'from':voter1})
    gauge_controller.checkpoint_gauge(gauge1, {'from': voter1})
    gauge_controller.checkpoint_gauge(gauge2, {'from': voter2})

    # Here we hvae to poke the gauge/update the period
    tx = bribe.add_reward_amount(gauge1, token1, 1, {'from': token1_whale})

    userbal = token1.balanceOf(user)
    voterbal = token1.balanceOf(voter2)
    bribe.set_delegate(user, {'from': voter2})
    tx = bribe.claim_reward(gauge1, token1, {'from': voter2})
    assert bribe.reward_delegate(voter2) == user
    assert userbal < token1.balanceOf(user)
    assert voterbal == token1.balanceOf(voter2)

    chain.undo(1)

    # Get same results when we call on behalf of
    tx = bribe.claim_reward_for(voter2, gauge1, token1, {'from': user})
    assert bribe.reward_delegate(voter2) == user
    assert userbal < token1.balanceOf(user)
    assert voterbal == token1.balanceOf(voter2)

    chain.undo(1)

    # Get same results when we call on behalf of
    bribe.clear_delegate({'from': voter2})
    tx = bribe.claim_reward_for(voter2, gauge1, token1, {'from': user})
    assert bribe.reward_delegate(voter2) != user
    assert userbal == token1.balanceOf(user)
    assert voterbal < token1.balanceOf(voter2)

def change_owner(
    token1, token2, token1_whale, bribe, gov, accounts, WEEK, user,
    token2_whale, gauge1, gauge2, gauge_controller, voter1, voter2
):
    bribe.set_owner(user, {'from': gov})
    bribe.accept_owner({'from': user})
    assert bribe.owner() == user
    bribe.set_owner(voter1, {'from': user})
    assert bribe.owner() == user
    bribe.accept_owner({'from': voter1})
    assert bribe.owner() == voter1

def test_checkpoint_gauge(
    token1, token2, token1_whale, bribe, gov, accounts, WEEK, user,
    token2_whale, gauge1, gauge2, gauge_controller, voter1, voter2
):
    token1.approve(bribe, 2**256-1, {'from': token1_whale})
    tx = bribe.add_reward_amount(gauge1, token1, 1_000_000e18, {'from': token1_whale})

    chain.sleep(WEEK)
    chain.mine(1)

    b1 = gauge_controller.time_weight(gauge1)
    b2 = gauge_controller.time_weight(gauge2)
    gauge_controller.checkpoint({'from':voter1})
    gauge_controller.checkpoint_gauge(gauge1, {'from': voter1})
    gauge_controller.checkpoint_gauge(gauge2, {'from': voter2})
    a1 = gauge_controller.time_weight(gauge1)
    a2 = gauge_controller.time_weight(gauge2)
    assert a1 > b1 and a2 > b2



def test(gauge1):
    gauge = gauge1
    WEEK = 86400 * 7
    period = int(chain.time() / WEEK) * WEEK
    decimals = 10**18
    gauge_controller = Contract("0x2F50D538606Fa9EDD2B11E2446BEb18C9D5846bB")
    yearn_voter = "0xF147b8125d2ef93FB6965Db97D6746952a133934"
    convex_voter = "0x989AEb4d175e16225E39E87d0D97A3360524AD80"
    total_slope = gauge_controller.points_weight(gauge, period).dict()["slope"] / decimals
    y_slope = gauge_controller.vote_user_slopes(yearn_voter, gauge).dict()["slope"] / decimals
    c_slope = gauge_controller.vote_user_slopes(convex_voter, gauge).dict()["slope"] / decimals

    print(f'Total: {total_slope}\nConvex: {c_slope}\nYearn: {y_slope}')

def test_claimable(token1, token2, token1_whale, bribe, user,
    token2_whale, gauge1, gauge2, gauge_controller, voter1, voter2
):

    WEEK = 86400 * 7
    period = int(chain.time() / WEEK) * WEEK

    # Poke gauges
    bribe.claim_reward(gauge1, token1, {'from':user})
    bribe.claim_reward(gauge2, token2, {'from':user})

    token1.approve(bribe, 2**256-1, {'from': token1_whale})
    token2.approve(bribe, 2**256-1, {'from': token2_whale})

    before1 = bribe.claimable(voter1, gauge1, token1)
    before2 = bribe.claimable(voter1, gauge1, token1)
    bribe.add_reward_amount(gauge1, token1, 2_000e18, {'from': token1_whale})
    bribe.add_reward_amount(gauge2, token2, 5_000e18, {'from': token2_whale})
    after1 = bribe.claimable(voter1, gauge1, token1)
    after2 = bribe.claimable(voter2, gauge2, token2)
    # Ensure claimable amount doesn't change. 
    # This test verifies that user must wait until following week to claim newly added rewards
    assert before1 == after1
    assert before2 == after2

    chain.sleep(WEEK)
    chain.mine(1)
    gauge_controller.checkpoint({'from':voter1})
    gauge_controller.checkpoint_gauge(gauge1, {'from': voter1})
    gauge_controller.checkpoint_gauge(gauge2, {'from': voter2})
    with brownie.reverts():
        bribe.claimable(voter1, gauge1, token1)
        bribe.claimable(voter1, gauge2, token2)

    bribe.claim_reward(gauge1, token1, {'from':user})
    bribe.claim_reward(gauge2, token2, {'from':user})
    bribe.claimable(voter1, gauge1, token1)
    bribe.claimable(voter1, gauge2, token2)