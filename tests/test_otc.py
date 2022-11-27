import brownie
from brownie import Contract, accounts, chain, ZERO_ADDRESS
import pytest
from utils import to_address


def test_standard_operation(
    token1,
    token2,
    token1_whale,
    bribe,
    user,
    otc,
    token2_whale,
    gauge1,
    gauge2,
    gauge_controller,
    voter1,
    voter2,
):
    WEEK = 86400 * 7
    require_vecrv = 2_000_000 * 1e18

    token1.approve(otc, 50_000 * 1e18, {"from": token1_whale})
    whale_bal = token1.balanceOf(token1_whale)
    fee_receiver = otc.feeRecipient()

    current_votes = otc.votedAmount(gauge1, voter2)
    print(current_votes / 1e18)

    t1 = otc.setupBribe(
        voter2, gauge1, token1, 10_000 * 1e18, require_vecrv, 4, {"from": token1_whale}
    )
    offer = t1.events["NewBribeOffer"]

    id = offer["id"]

    offer1 = otc.bribeOffers(0).dict()
    print(offer1)
    assert id == 0
    assert offer["voter"] == voter2 == offer1["voter"]
    assert offer["gauge"] == gauge1 == offer1["gauge"]
    assert offer["briber"] == token1_whale == offer1["briber"]
    assert offer["requiredVeCrvAmount"] == require_vecrv
    assert offer["requiredVeCrvAmount"] == offer1["requiredVeCrvAmount"]
    assert offer["bribeToken"] == token1 == offer1["bribeToken"]
    assert offer["weeklyBribeAmount"] == 10_000 * 1e18 == offer1["weeklyBribeAmount"]
    assert offer["start"] == chain.time() // WEEK * WEEK + WEEK == offer1["start"]
    assert offer["numWeeks"] == 4 == offer1["numberOfWeeks"]
    assert (
        token1.balanceOf(otc)
        == offer["weeklyBribeAmount"] * 4
        == offer1["weeklyBribeAmount"] * 4
    )
    assert (token1.balanceOf(otc) ==10_000 * 1e18 * 4)

    assert current_votes > require_vecrv
    with brownie.reverts():
        otc.claimable(id, 0)
    assert otc.claimable(id, 1) == False

    chain.sleep(WEEK)
    chain.mine(1)
    print(chain.time())

    print(offer1["requiredVeCrvAmount"])
    print(otc.votedAmount(gauge1, voter2) / 1e18)
    assert otc.claimable(id, 1) == True

    chain.sleep(3 * WEEK)
    chain.mine(1)
    assert otc.claimable(id, 1) == True
    assert otc.claimable(id, 2) == True
    assert otc.claimable(id, 3) == True
    assert otc.claimable(id, 4) == True
    assert otc.claimable(id, 5) == False

    beforeBal = token1.balanceOf(voter2)
    before_receiver = token1.balanceOf(fee_receiver)
    otc.claimBribe(id, 2, {"from": voter2})
    assert token1.balanceOf(otc) == offer["weeklyBribeAmount"] * 3
    fee = offer["weeklyBribeAmount"] * 100 // 10_000
    assert token1.balanceOf(voter2) - beforeBal == offer["weeklyBribeAmount"] - fee

    assert token1.balanceOf(fee_receiver) - before_receiver == fee
    assert otc.claimable(id, 1) == True
    assert otc.claimable(id, 2) == False
    assert otc.claimable(id, 3) == True
    assert otc.claimable(id, 4) == True

    chain.sleep(10 * WEEK)
    chain.mine(1)

    assert otc.retrievable(id) == True
    with brownie.reverts():
        otc.retrieveAll(id, {"from": voter2})

    with brownie.reverts():
        otc.retrieveUnclaimedBribesPerWeek(id, 2, {"from": token1_whale})
    otc.retrieveUnclaimedBribesPerWeek(id, 3, {"from": token1_whale})
    assert otc.claimable(id, 1) == True
    assert otc.claimable(id, 2) == False
    assert otc.claimable(id, 3) == False
    assert otc.claimable(id, 4) == True

    otc.retrieveAll(id, {"from": token1_whale})

    offer2 = otc.bribeOffers(0).dict()
    assert offer2["briber"] == ZERO_ADDRESS
    assert offer2["voter"] == ZERO_ADDRESS
    assert token1.balanceOf(token1_whale) == whale_bal - offer["weeklyBribeAmount"]
    assert token1.balanceOf(otc) == 0


def test_not_voted_enough(
    token1,
    token2,
    token1_whale,
    bribe,
    user,
    otc,
    token2_whale,
    gauge1,
    gauge2,
    gauge_controller,
    voter1,
    voter2,
):
    WEEK = 86400 * 7
    require_vecrv = 2_000_000 * 1e18
    weekly_bribe = 10_000 * 1e18

    chain.sleep(2 * WEEK)
    chain.mine(1)

    gauge_controller.vote_for_gauge_weights(gauge1, 0, {"from": voter2})

    chain.sleep(2 * WEEK)
    chain.mine(1)

    token1.approve(otc, 50_000 * 1e18, {"from": token1_whale})
    whale_bal = token1.balanceOf(token1_whale)

    current_votes = otc.votedAmount(gauge1, voter2)
    assert current_votes == 0

    t1 = otc.setupBribe(
        voter2, gauge1, token1, weekly_bribe, require_vecrv, 4, {"from": token1_whale}
    )
    offer = t1.events["NewBribeOffer"]

    id = offer["id"]

    chain.sleep(WEEK)
    chain.mine(1)

    assert otc.claimable(id, 1) == False
    assert otc.claimable(id, 2) == False

    with brownie.reverts():
        otc.claimBribe(id, 1, {"from": voter2})

    otc.retrieveUnclaimedBribesPerWeek(id, 1, {"from": token1_whale})

    token1.balanceOf(otc) == weekly_bribe * 3
    chain.sleep(WEEK)
    chain.mine(1)
    gauge_controller.vote_for_gauge_weights(gauge1, 4000, {"from": voter2})
    assert otc.claimable(id, 2) == False
    assert otc.claimable(id, 3) == False
    otc.retrieveUnclaimedBribesPerWeek(id, 2, {"from": token1_whale})

    token1.balanceOf(otc) == weekly_bribe * 2

    chain.sleep(WEEK)
    chain.mine(1)
    assert otc.claimable(id, 3) == True
    assert otc.claimable(id, 4) == False
    with brownie.reverts():
        otc.claimBribe(id, 4, {"from": voter2})
    otc.claimBribe(id, 3, {"from": voter2})

    chain.sleep(WEEK * 5)
    chain.mine(1)
    otc.retrieveUnclaimedBribesPerWeek(id, 4, {"from": token1_whale})
    offer2 = otc.bribeOffers(0).dict()
    assert offer2["briber"] == ZERO_ADDRESS
    assert offer2["voter"] == ZERO_ADDRESS
    assert token1.balanceOf(otc) == 0

def test_future_claim(
    token1,
    token2,
    token1_whale,
    bribe,
    user,
    otc,
    token2_whale,
    gauge1,
    gauge2,
    gauge_controller,
    voter1,
    voter2,
):
    WEEK = 86400 * 7
    require_vecrv = 2_000_000 * 1e18

    token1.approve(otc, 50_000 * 1e18, {"from": token1_whale})
    whale_bal = token1.balanceOf(token1_whale)
    fee_receiver = otc.feeRecipient()

    current_votes = otc.votedAmount(gauge1, voter2)
    print(current_votes / 1e18)

    t1 = otc.setupBribe(
        voter2, gauge1, token1, 10_000 * 1e18, require_vecrv, 10, {"from": token1_whale}
    )
    offer = t1.events["NewBribeOffer"]

    id = offer["id"]

    offer1 = otc.bribeOffers(0).dict()

    assert False
    print(offer1)
    assert id == 0
    assert offer["voter"] == voter2 == offer1["voter"]
    assert offer["gauge"] == gauge1 == offer1["gauge"]
    assert offer["briber"] == token1_whale == offer1["briber"]
    assert offer["requiredVeCrvAmount"] == require_vecrv
    assert offer["requiredVeCrvAmount"] == offer1["requiredVeCrvAmount"]
    assert offer["bribeToken"] == token1 == offer1["bribeToken"]
    assert offer["weeklyBribeAmount"] == 10_000 * 1e18 == offer1["weeklyBribeAmount"]
    assert offer["start"] == chain.time() // WEEK * WEEK + WEEK == offer1["start"]
    assert offer["numWeeks"] == 4 == offer1["numberOfWeeks"]
    assert (
        token1.balanceOf(otc)
        == offer["weeklyBribeAmount"] * 4
        == offer1["weeklyBribeAmount"] * 4
    )
    assert (token1.balanceOf(otc) ==10_000 * 1e18 * 4)

    assert current_votes > require_vecrv
    with brownie.reverts():
        otc.claimable(id, 0)
    assert otc.claimable(id, 1) == False

    chain.sleep(WEEK)
    chain.mine(1)
    print(chain.time())