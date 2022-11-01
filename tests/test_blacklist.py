import brownie
from brownie import Contract, accounts, chain
import pytest

def test_blacklist_bias(
    token1, token2, token1_whale, bribe, gov, user,
    token2_whale, gauge1, gauge2, gauge_controller, voter1, voter2
):

    bribe.add_to_blacklist(voter2, {'from': gov}) # YEARN
    print(f'Blacklist --> \n{list(bribe.get_blacklist())}')
    assert len(list(bribe.get_blacklist())) == 1
    WEEK = 86400 * 7
    period = int(chain.time() / WEEK) * WEEK

    # Add some bribes
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
    tx = bribe.add_reward_amount(gauge1, token1, 1e18, {'from': token1_whale})
    period_updated = tx.events["PeriodUpdated"]
    assert period_updated['blacklisted_bias'] > 0
    tx = bribe.add_reward_amount(gauge2, token2, 1e18, {'from': token2_whale})
    period_updated = tx.events["PeriodUpdated"]
    assert period_updated['blacklisted_bias'] == 0
    assert before1 == after1
    assert before2 == after2

    # Here we unblacklist -- 
    # IMPORTANTLY we do this before the following week has started, otherwise 
    bribe.remove_from_blacklist(voter2, {'from': gov}) # YEARN
    assert len(list(bribe.get_blacklist())) == 0
    chain.sleep(WEEK)
    chain.mine(1)
    gauge_controller.checkpoint({'from':voter1})
    gauge_controller.checkpoint_gauge(gauge1, {'from': voter1})
    gauge_controller.checkpoint_gauge(gauge2, {'from': voter2})
    print(gauge_controller.vote_user_slopes(voter1, gauge1).dict())
    print(gauge_controller.vote_user_slopes(voter2, gauge2).dict())
    tx = bribe.add_reward_amount(gauge1, token1, 1, {'from': token1_whale})
    period_updated = tx.events["PeriodUpdated"]
    total_bribe = token1.balanceOf(bribe)/1e18
    tx = bribe.claim_reward(gauge1, token1, {'from':voter2})
    total_claimed = tx.events['RewardClaimed']['amount']/1e18
    print(f'Claimed: {total_claimed}')
    print(f'Total: {total_bribe}')
    print(f'Percent: {round(total_claimed/total_bribe*100, 3)}%')

    user_point = gauge_controller.vote_user_slopes(voter2, gauge1).dict()
    user_lock_end = user_point['end']
    user_slope = user_point['slope']
    # user_bias1 = user_slope * (user_lock_end - (bribe.current_period() + WEEK)) # Here we use current_period instead of chain.time()
    # user_bias2 = user_slope * (user_lock_end - chain.time()) # Here we use current_period instead of chain.time()
    user_bias3 = user_slope * (user_lock_end - bribe.current_period()) # Here we use current_period instead of chain.time()
    # user_bias4 = user_slope * (user_lock_end - (bribe.current_period() - WEEK)) # Here we use current_period instead of chain.time()
    gauge_bias = gauge_controller.points_weight(gauge1,period_updated['period'])['bias']
    print(f'\nUser Bias: {user_bias3}')
    print(f'Gauge Bias: {gauge_bias}')
    # print(f'Percent Bias: {round(user_bias1/gauge_bias*100, 3)}%')
    # print(f'Percent Bias: {round(user_bias2/gauge_bias*100, 3)}%')
    print(f'Percent Bias: {round(user_bias3/gauge_bias*100, 3)}%')
    # print(f'Percent Bias: {round(user_bias4/gauge_bias*100, 3)}%')