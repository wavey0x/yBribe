/**
 *Submitted for verification at Etherscan.io on 2021-08-13
*/

// SPDX-License-Identifier: MIT
pragma solidity 0.8.6;

interface GaugeController {
    struct VotedSlope {
        uint slope;
        uint power;
        uint end;
    }
    
    struct Point {
        uint bias;
        uint slope;
    }
    
    function vote_user_slopes(address, address) external view returns (VotedSlope memory);
    function last_user_vote(address, address) external view returns (uint);
    function points_weight(address, uint256) external view returns (Point memory);
    function checkpoint_gauge(address) external;
}

interface ve {
    function get_last_user_slope(address) external view returns (int128);
}

interface erc20 { 
    function transfer(address recipient, uint256 amount) external returns (bool);
    function decimals() external view returns (uint8);
    function balanceOf(address) external view returns (uint);
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function approve(address spender, uint amount) external returns (bool);
}

contract BribeV3 {

    event RewardAdded(address indexed briber, address indexed gauge, address indexed reward_token, uint amount);
    event RewardClaimed(address indexed user, address indexed gauge, address indexed reward_token, uint amount);
    event Blacklisted(address user);
    event RemovedFromBlacklist(address user);
    event SetRewardDelegate(address user, address delegate);
    event ClearRewardDelegate(address user, address delegate);
    event ChangeOwner(address owner);

    uint constant WEEK = 86400 * 7;
    uint constant PRECISION = 10**18;
    GaugeController constant GAUGE = GaugeController(0x2F50D538606Fa9EDD2B11E2446BEb18C9D5846bB);
    ve constant VE = ve(0x5f3b5DfEb7B28CDbD7FAba78963EE202a494e2A2);
    
    mapping(address => mapping(address => uint)) public _claims_per_gauge;
    mapping(address => mapping(address => uint)) public _reward_per_gauge;
    
    mapping(address => mapping(address => uint)) public reward_per_token;
    mapping(address => mapping(address => uint)) public active_period;
    mapping(address => mapping(address => mapping(address => uint))) public last_user_claim;
    
    mapping(address => address[]) public _rewards_per_gauge;
    mapping(address => address[]) public _gauges_per_reward;
    mapping(address => mapping(address => bool)) public _rewards_in_gauge;

    address public owner = 0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52;
    address public pending_owner;
    address[] public blacklist;
    mapping(address => address) public reward_delegate;
    
    function _add(address gauge, address reward) internal {
        if (!_rewards_in_gauge[gauge][reward]) {
            _rewards_per_gauge[gauge].push(reward);
            _gauges_per_reward[reward].push(gauge);
            _rewards_in_gauge[gauge][reward] = true;
        }
    }
    
    function rewards_per_gauge(address gauge) external view returns (address[] memory) {
        return _rewards_per_gauge[gauge];
    }
    
    function gauges_per_reward(address reward) external view returns (address[] memory) {
        return _gauges_per_reward[reward];
    }
    
    function _update_period(address gauge, address reward_token) internal returns (uint) {
        uint _period = active_period[gauge][reward_token];
        if (block.timestamp >= _period + WEEK) {
            _period = block.timestamp / WEEK * WEEK;
            GAUGE.checkpoint_gauge(gauge);
            uint _slope = GAUGE.points_weight(gauge, _period).slope;
            _slope -= get_blacklisted_slope(gauge);
            uint _amount = _reward_per_gauge[gauge][reward_token] - _claims_per_gauge[gauge][reward_token];
            reward_per_token[gauge][reward_token] = _amount * PRECISION / _slope;
            active_period[gauge][reward_token] = _period;
        }
        return _period;
    }
    
    function add_reward_amount(address gauge, address reward_token, uint amount) external returns (bool) {
        _safeTransferFrom(reward_token, msg.sender, address(this), amount);
        _update_period(gauge, reward_token);
        _reward_per_gauge[gauge][reward_token] += amount;
        _add(gauge, reward_token);
        emit RewardAdded(msg.sender, gauge, reward_token, amount);
        return true;
    }
    
    function tokens_for_bribe(address user, address gauge, address reward_token) external view returns (uint) {
        return uint(int(VE.get_last_user_slope(user))) * reward_per_token[gauge][reward_token] / PRECISION;
    }
    
    function claimable(address user, address gauge, address reward_token) external view returns (uint) {
        if(is_blacklisted(user)){
            return 0;
        }
        uint _period = block.timestamp / WEEK * WEEK;
        uint _amount = 0;
        if (last_user_claim[user][gauge][reward_token] < _period) {
            uint _last_vote = GAUGE.last_user_vote(user, gauge);
            if (_last_vote < _period) {
                uint _slope = GAUGE.vote_user_slopes(user, gauge).slope;
                _amount = _slope * reward_per_token[gauge][reward_token] / PRECISION;
            }
        }
        return _amount;
    }
    
    
    function claim_reward(address gauge, address reward_token) external returns (uint) {
        return _claim_reward(msg.sender, gauge, reward_token);
    }

    function claim_reward_for_many(address[] calldata _users, address[] calldata _gauges, address[] calldata _reward_tokens) external returns (uint) {
        require(_users.length == _gauges.length && _users.length == _reward_tokens.length, "!lengths");
        uint length = _users.length;
        for (uint256 i = 0; i < length; i++) {
            _claim_reward(_users[i], _gauges[i], _reward_tokens[i]);
        }
        return length;
    }

    function claim_reward_for(address user, address gauge, address reward_token) external returns (uint) {
        return _claim_reward(user, gauge, reward_token);
    }
    
    function _claim_reward(address user, address gauge, address reward_token) internal returns (uint) {
        if(is_blacklisted(user)){
            return 0;
        }
        uint _period = _update_period(gauge, reward_token);
        uint _amount = 0;
        if (last_user_claim[user][gauge][reward_token] < _period) {
            last_user_claim[user][gauge][reward_token] = _period;
            uint _last_vote = GAUGE.last_user_vote(user, gauge);
            if (_last_vote < _period) {
                uint _slope = GAUGE.vote_user_slopes(user, gauge).slope;
                _amount = _slope * reward_per_token[gauge][reward_token] / PRECISION;
                if (_amount > 0) {
                    _claims_per_gauge[gauge][reward_token] += _amount;
                    address delegate = reward_delegate[user];
                    address recipient = delegate == address(0) ? user : delegate;
                    _safeTransfer(reward_token, recipient, _amount);
                    emit RewardClaimed(user, gauge, user, _amount);
                }
            }
        }
        return _amount;
    }
    
    function _safeTransfer(
        address token,
        address to,
        uint256 value
    ) internal {
        (bool success, bytes memory data) =
            token.call(abi.encodeWithSelector(erc20.transfer.selector, to, value));
        require(success && (data.length == 0 || abi.decode(data, (bool))));
    }
    
    function _safeTransferFrom(
        address token,
        address from,
        address to,
        uint256 value
    ) internal {
        (bool success, bytes memory data) =
            token.call(abi.encodeWithSelector(erc20.transferFrom.selector, from, to, value));
        require(success && (data.length == 0 || abi.decode(data, (bool))));
    }

    function get_blacklisted_slope(address _gauge) public view returns (uint) {
        uint slope;
        uint length = blacklist.length;
        for (uint i = 0; i < length; i++) {
            slope += GAUGE.vote_user_slopes(blacklist[i], _gauge).slope;
        }
        return slope;
    }

    function add_to_blacklist(address _user) external {
        require(msg.sender == owner, "!owner");

        uint length = blacklist.length;

        for (uint i = 0; i < length; i++) {
            require(blacklist[i] != _user, "!already");
        }
        blacklist.push(_user);
        emit Blacklisted(_user);
    }

    function remove_from_blacklist(address _user) external {
        require(msg.sender == owner, "!owner");
        uint length = blacklist.length;
        for (uint i = 0; i < length; i++) {
            if (blacklist[i] == _user) {
                blacklist[i] = blacklist[length-1];
                blacklist.pop();
                emit RemovedFromBlacklist(_user);
                return;
            }
        }
    }

    function is_blacklisted(address address_to_check) public view returns (bool) {
        uint list_length = blacklist.length;
        for (uint i = 0; i < list_length; i++) {
            if (blacklist[i] == address_to_check) {
                return true;
            }
        }
        return false;
    }

    function set_delegate(address _delegate) external {
        require (_delegate != msg.sender, "Can't delegate to self");
        require (_delegate != address(0), "Can't delegate to 0x0");
        address current_delegate = reward_delegate[msg.sender];
        require (_delegate != current_delegate, "Already delegated to this address");
        
        // Update delegation mapping
        reward_delegate[msg.sender] = _delegate;
        
        if (current_delegate != address(0)) {
            emit ClearRewardDelegate(msg.sender, current_delegate);
        }

        emit SetRewardDelegate(msg.sender, _delegate);
    }

    function clear_delegate() external {
        address current_delegate = reward_delegate[msg.sender];
        require (current_delegate != address(0), "No delegate set");
        
        // update delegation mapping
        reward_delegate[msg.sender]= address(0);
        
        emit ClearRewardDelegate(msg.sender, current_delegate);
    }

    function set_owner(address _owner) external {
        require(msg.sender == owner, "!owner");
        pending_owner = _owner;
    }

    function accept_owner() external {
        address _pending_owner = pending_owner;
        require(msg.sender == _pending_owner, "!pending_owner");
        
        owner = _pending_owner;
        emit ChangeOwner(_pending_owner);
        pending_owner = address(0);
    }
    
}