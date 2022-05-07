import pytest, requests
from brownie import config, chain
from brownie import Contract

@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass


@pytest.fixture
def gov(accounts):
    yield accounts.at("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52", force=True)


@pytest.fixture
def user(accounts):
    yield accounts[0]


@pytest.fixture
def rewards(accounts):
    yield accounts[1]


@pytest.fixture
def guardian(accounts):
    yield accounts[2]


@pytest.fixture
def management(accounts):
    yield accounts[3]


@pytest.fixture
def strategist(accounts):
    yield accounts[4]


@pytest.fixture
def keeper(accounts):
    yield accounts[5]


@pytest.fixture
def token1(): # SPELL
    token_address = "0x090185f2135308BaD17527004364eBcC2D37e5F6"
    yield Contract(token_address)


@pytest.fixture
def token2(): # INV
    token_address = "0x41D5D79431A913C4aE7d69a668ecdfE5fF9DFB68"
    yield Contract(token_address)

@pytest.fixture
def gauge1(): # MIM
    return Contract("0xd8b712d29381748dB89c36BCa0138d7c75866ddF")

@pytest.fixture
def gauge2(): # DOLA
    return Contract("0x8Fa728F393588E8D8dD1ca397E9a710E53fA553a")


@pytest.fixture
def token1_whale(accounts):
    return accounts.at("0x090185f2135308BaD17527004364eBcC2D37e5F6", force=True)

@pytest.fixture
def token2_whale(accounts):
    return accounts.at("0x1637e4e9941D55703a7A5E7807d6aDA3f7DCD61B", force=True)


@pytest.fixture
def gauge_controller():
    return Contract("0x2F50D538606Fa9EDD2B11E2446BEb18C9D5846bB")

@pytest.fixture
def bribe(user, BribeV3):
    bribe = user.deploy(BribeV3)
    return bribe

@pytest.fixture
def WEEK():
    return 86400 * 7

@pytest.fixture(scope="session")
def RELATIVE_APPROX():
    # making this more lenient bc of single sided deposits incurring slippage
    yield 1e-3

@pytest.fixture
def voter1(accounts):
    return accounts.at("0x989AEb4d175e16225E39E87d0D97A3360524AD80", force=True)

@pytest.fixture
def voter2(accounts):
    return accounts.at("0xF147b8125d2ef93FB6965Db97D6746952a133934", force=True)