import brownie
from brownie import Contract, accounts, chain
import pytest
from utils import to_address


def test_fresh_gauge(
    token1,
    token2,
    token1_whale,
    bribe,
    user,
    fresh_token,
    fresh_token_whale,
    token2_whale,
    gauge1,
    gauge2,
    gauge_controller,
    voter1,
    voter2,
    vecrv,
):

    WEEK = 86400 * 7
    YEAR = 60 * 60 * 24 * 365
    period = int(chain.time() / WEEK) * WEEK

    admin = gauge_controller.admin()
    fresh_gauge = to_address(1)
    fresh_token = Contract("0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984")
    gauge_controller.add_gauge(fresh_gauge, 2, {"from": admin})
    gauge_controller.vote_for_gauge_weights(fresh_gauge, 19, {"from": user})
    fast_forward(gauge_controller, fresh_gauge, gauge1, gauge2, voter1, voter2)
    tx = bribe.add_reward_amount(
        fresh_gauge, fresh_token, 1e18, {"from": fresh_token_whale}
    )
    # Ensure bribes are not immediately claimable by prior voters in same period bribe was added (this was a bug in old contract)
    assert bribe.claimable(user, fresh_gauge, fresh_token) == 0

    fast_forward(gauge_controller, fresh_gauge, gauge1, gauge2, voter1, voter2)

    slope = gauge_controller.vote_user_slopes(user, fresh_gauge).dict()["slope"]
    end = gauge_controller.vote_user_slopes(user, fresh_gauge).dict()["end"]
    last_vote = gauge_controller.last_user_vote(user, fresh_gauge)
    derived_user_bias = slope * (end - last_vote)

    gauge_bias = gauge_controller.points_weight(
        fresh_gauge, bribe.current_period()
    ).dict()["bias"]
    print(f"--- BIAS STATS ---")
    print(f"{derived_user_bias/1e18}")
    print(f"{gauge_bias/1e18}")
    tx = bribe.claim_reward(fresh_gauge, fresh_token, {"from": user})

    tx = bribe.add_reward_amount(
        fresh_gauge, fresh_token, 3e18, {"from": fresh_token_whale}
    )
    fast_forward(gauge_controller, fresh_gauge, gauge1, gauge2, voter1, voter2)
    fast_forward(gauge_controller, fresh_gauge, gauge1, gauge2, voter1, voter2)

    slope = gauge_controller.vote_user_slopes(user, fresh_gauge).dict()["slope"]
    end = gauge_controller.vote_user_slopes(user, fresh_gauge).dict()["end"]
    last_vote = gauge_controller.last_user_vote(user, fresh_gauge)
    derived_user_bias = slope * (end - last_vote)

    gauge_bias = gauge_controller.points_weight(
        fresh_gauge, bribe.current_period()
    ).dict()["bias"]
    print(f"--- BIAS STATS ---")
    print(f"{derived_user_bias/1e18}")
    print(f"{gauge_bias/1e18}")
    tx = bribe.claim_reward(fresh_gauge, fresh_token, {"from": user})

    gauge_controller.vote_for_gauge_weights(
        "0xD6e48Cc0597a1Ee12a8BeEB88e22bFDb81777164", 10, {"from": voter1}
    )
    gauge_controller.vote_for_gauge_weights(fresh_gauge, 10, {"from": voter1})

    tx = bribe.add_reward_amount(
        fresh_gauge, fresh_token, 1e18, {"from": fresh_token_whale}
    )
    fast_forward(gauge_controller, fresh_gauge, gauge1, gauge2, voter1, voter2)
    vecrv.increase_unlock_time(chain.time() + (YEAR * 4), {"from": user})
    fast_forward(gauge_controller, fresh_gauge, gauge1, gauge2, voter1, voter2)

    slope = gauge_controller.vote_user_slopes(user, fresh_gauge).dict()["slope"]
    end = gauge_controller.vote_user_slopes(user, fresh_gauge).dict()["end"]
    last_vote = gauge_controller.last_user_vote(user, fresh_gauge)
    derived_user_bias = slope * (end - last_vote)

    gauge_bias = gauge_controller.points_weight(
        fresh_gauge, bribe.current_period() + WEEK
    ).dict()["bias"]
    print(f"--- BIAS STATS ---")
    print(f"{derived_user_bias/1e18}")
    print(f"{gauge_bias/1e18}")
    vecrv.increase_unlock_time(chain.time() + (YEAR * 4), {"from": user})
    tx = bribe.claim_reward(fresh_gauge, fresh_token, {"from": user})
    tx = bribe.claim_reward(fresh_gauge, fresh_token, {"from": voter1})
    assert (
        fresh_token.balanceOf(bribe) < 1e15
    )  # we should be within rounding error territory


def fast_forward(gauge_controller, fresh_gauge, gauge1, gauge2, voter1, voter2):
    WEEK = 86400 * 7
    chain.sleep(WEEK)
    chain.mine(1)
    gauge_controller.checkpoint({"from": voter1})
    gauge_controller.checkpoint_gauge(gauge1, {"from": voter1})
    gauge_controller.checkpoint_gauge(gauge2, {"from": voter2})
    gauge_controller.checkpoint_gauge(fresh_gauge, {"from": voter2})
