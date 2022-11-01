import brownie
from brownie import Contract, accounts, chain
import pytest
from utils import to_address

def test_fresh_gauge(
    token1, token2, token1_whale, bribe, user, fresh_token, fresh_token_whale,
    token2_whale, gauge1, gauge2, gauge_controller, voter1, voter2, vecrv
):

    WEEK = 86400 * 7
    YEAR = 60 * 60 * 24 * 365
    period = int(chain.time() / WEEK) * WEEK

    admin = gauge_controller.admin()
    fresh_gauge = to_address(1)
    fresh_token = Contract('0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984')
    gauge_controller.add_gauge(fresh_gauge, 2, {'from': admin})
    gauge_controller.vote_for_gauge_weights(fresh_gauge, 19, {'from':user})

    tx = bribe.add_reward_amount(fresh_gauge, fresh_token, 1e18, {'from': fresh_token_whale})

    fast_forward(gauge_controller, fresh_gauge, gauge1, gauge2, voter1, voter2)

    slope = gauge_controller.vote_user_slopes(user, fresh_gauge).dict()['slope']
    end = gauge_controller.vote_user_slopes(user, fresh_gauge).dict()['end']
    last_vote = gauge_controller.last_user_vote(user, fresh_gauge)
    derived_user_bias = slope * (end - last_vote)

    gauge_bias = gauge_controller.points_weight(fresh_gauge, bribe.current_period()).dict()['bias']
    print(f'--- BIAS STATS ---')
    print(f'{derived_user_bias/1e18}')
    print(f'{gauge_bias/1e18}')
    tx = bribe.claim_reward(fresh_gauge, fresh_token, {'from':user})

    tx = bribe.add_reward_amount(fresh_gauge, fresh_token, 3e18, {'from': fresh_token_whale})
    fast_forward(gauge_controller, fresh_gauge, gauge1, gauge2, voter1, voter2)
    fast_forward(gauge_controller, fresh_gauge, gauge1, gauge2, voter1, voter2)

    slope = gauge_controller.vote_user_slopes(user, fresh_gauge).dict()['slope']
    end = gauge_controller.vote_user_slopes(user, fresh_gauge).dict()['end']
    last_vote = gauge_controller.last_user_vote(user, fresh_gauge)
    derived_user_bias = slope * (end - last_vote)

    gauge_bias = gauge_controller.points_weight(fresh_gauge, bribe.current_period()).dict()['bias']
    print(f'--- BIAS STATS ---')
    print(f'{derived_user_bias/1e18}')
    print(f'{gauge_bias/1e18}')
    tx = bribe.claim_reward(fresh_gauge, fresh_token, {'from':user})

    gauge_controller.vote_for_gauge_weights('0xD6e48Cc0597a1Ee12a8BeEB88e22bFDb81777164', 10, {'from':voter1})
    gauge_controller.vote_for_gauge_weights(fresh_gauge, 10, {'from':voter1})

    tx = bribe.add_reward_amount(fresh_gauge, fresh_token, 1e18, {'from': fresh_token_whale})
    fast_forward(gauge_controller, fresh_gauge, gauge1, gauge2, voter1, voter2)
    vecrv.increase_unlock_time(chain.time() + (YEAR * 4),{'from':user})
    fast_forward(gauge_controller, fresh_gauge, gauge1, gauge2, voter1, voter2)

    slope = gauge_controller.vote_user_slopes(user, fresh_gauge).dict()['slope']
    end = gauge_controller.vote_user_slopes(user, fresh_gauge).dict()['end']
    last_vote = gauge_controller.last_user_vote(user, fresh_gauge)
    derived_user_bias = slope * (end - last_vote)

    gauge_bias = gauge_controller.points_weight(fresh_gauge, bribe.current_period()+WEEK).dict()['bias']
    print(f'--- BIAS STATS ---')
    print(f'{derived_user_bias/1e18}')
    print(f'{gauge_bias/1e18}')
    vecrv.increase_unlock_time(chain.time() + (YEAR * 4),{'from':user})
    tx = bribe.claim_reward(fresh_gauge, fresh_token, {'from':user})
    tx = bribe.claim_reward(fresh_gauge, fresh_token, {'from':voter1})
    assert False
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
    
    print(gauge_controller.vote_user_slopes(voter1, gauge1).dict())
    print(gauge_controller.vote_user_slopes(voter2, gauge2).dict())
    assert bribe.claimable(voter1, gauge1, token1) > after1
    assert bribe.claimable(voter2, gauge2, token2) > after2

    gauge_controller.vote_for_gauge_weights(gauge2, 0,{'from': voter1})
    gauge_controller.vote_for_gauge_weights(gauge2, 0,{'from': voter2})

def fast_forward(gauge_controller, fresh_gauge, gauge1, gauge2, voter1, voter2):
    WEEK = 86400 * 7
    chain.sleep(WEEK)
    chain.mine(1)
    gauge_controller.checkpoint({'from':voter1})
    gauge_controller.checkpoint_gauge(gauge1, {'from': voter1})
    gauge_controller.checkpoint_gauge(gauge2, {'from': voter2})
    gauge_controller.checkpoint_gauge(fresh_gauge, {'from': voter2})