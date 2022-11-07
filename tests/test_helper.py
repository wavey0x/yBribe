import brownie
from brownie import Contract, accounts, chain
import pytest
from utils import to_address


def test_operation(helper, user, live_bribe, token1, token1_whale, gauge1):
    gauge = "0x05255C5BD33672b9FEA4129C13274D1E6193312d"
    token = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    print(helper.getNewRewardPerToken.call(gauge, token))

    # test abra adding
    token1.approve(live_bribe, 2**256 - 1, {"from": token1_whale})
    live_bribe.add_reward_amount(gauge1, token1, 1e18, {"from": token1_whale})
    predicted = helper.getNewRewardPerToken.call(gauge1, token1)
    print(predicted)

    chain.sleep(2 * 60 * 60 * 24)
    live_bribe.add_reward_amount(
        gauge1, token1, 1e18, {"from": token1_whale}
    )  # this till update period
    real = live_bribe.reward_per_token(gauge1, token1)

    # assert that our predicted for the week is correct
    assert predicted == real
