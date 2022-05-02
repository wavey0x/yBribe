import json
from brownie import (
    Contract,
    ZERO_ADDRESS,
    chain,
    accounts,
    ZERO_ADDRESS,
)

def main():
    WEEK = 86400 * 7
    period = int(chain.time() / WEEK) * WEEK
    decimals = 10**18
    bribev2 = Contract("0x7893bbb46613d7a4FbcC31Dab4C9b823FfeE1026")
    spell = "0x090185f2135308BaD17527004364eBcC2D37e5F6"

    gauge_controller = Contract("0x2F50D538606Fa9EDD2B11E2446BEb18C9D5846bB")
    ib_gauge = "0xF5194c3325202F456c95c1Cf0cA36f8475C1949F"
    mim_gauge = "0xd8b712d29381748dB89c36BCa0138d7c75866ddF"
    dola_gauge = "0x8Fa728F393588E8D8dD1ca397E9a710E53fA553a"
    yearn_voter = "0xF147b8125d2ef93FB6965Db97D6746952a133934"
    convex_voter = "0x989AEb4d175e16225E39E87d0D97A3360524AD80"


    get_data(mim_gauge)
    print("----")

    # Amount of tokens available is defined at start of period

def get_data(gauge):
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

def sim_bribev2():
    WEEK = 86400 * 7
    period = int(chain.time() / WEEK) * WEEK
    decimals = 10**18
    bribev2 = Contract("0x7893bbb46613d7a4FbcC31Dab4C9b823FfeE1026")
    spell = "0x090185f2135308BaD17527004364eBcC2D37e5F6"

    gauge_controller = Contract("0x2F50D538606Fa9EDD2B11E2446BEb18C9D5846bB")
    ib_gauge = "0xF5194c3325202F456c95c1Cf0cA36f8475C1949F"
    mim_gauge = "0xd8b712d29381748dB89c36BCa0138d7c75866ddF"
    dola_gauge = "0x8Fa728F393588E8D8dD1ca397E9a710E53fA553a"
    yearn_voter = accounts.at("0xF147b8125d2ef93FB6965Db97D6746952a133934", force=True)
    convex_voter = accounts.at("0x989AEb4d175e16225E39E87d0D97A3360524AD80", force=True)
    bribev2.claimable(convex_voter, mim_gauge, spell)
    gauge_controller.vote_for_gauge_weights(mim_gauge, 0,{'from': convex_voter})
    bribev2.claimable(convex_voter, mim_gauge, spell)
    get_data(mim_gauge)
    print("----")

