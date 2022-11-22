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
    function points_weight(address, uint) external view returns (Point memory);
    function checkpoint_gauge(address) external;
    function time_total() external view returns (uint);
    function gauge_types(address) external view returns (int128);
}

interface erc20 { 
    function transfer(address recipient, uint amount) external returns (bool);
    function decimals() external view returns (uint8);
    function balanceOf(address) external view returns (uint);
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function approve(address spender, uint amount) external returns (bool);
}

contract yBribe {

    event RewardAdded(address indexed briber, uint period, address indexed gauge, address indexed reward_token, uint amount, uint fee);
    event RewardScheduled(address indexed briber, uint period, address indexed gauge, address indexed reward_token, uint amount, uint fee, uint n_periods, uint delay);
    event RewardRetrieved(address indexed briber, address indexed gauge, address indexed reward_token, uint scheduled_period, uint amount);
    event NewTokenReward(address indexed gauge, address indexed reward_token); // Specifies unique token added for first time to gauge
    event RewardClaimed(address indexed user, address indexed gauge, address indexed reward_token, uint amount);
    event SetRewardRecipient(address indexed user, address recipient);
    event ClearRewardRecipient(address indexed user, address recipient);
    event SetClaimDelegate(address indexed user, address new_delegate);
    event ClearClaimDelegate(address indexed user, address cleared_delegate);
    event ChangeOwner(address owner);
    event PeriodUpdated(address indexed gauge, uint indexed period, uint amount, uint bias, uint omitted_bias);
    event FeeUpdated(uint fee);
    event SetFeeRecipient(address recipient);

    uint constant WEEK = 86400 * 7;
    uint constant PRECISION = 10**18;
    GaugeController constant GAUGE = GaugeController(0x2F50D538606Fa9EDD2B11E2446BEb18C9D5846bB);
    address constant BLOCKED_USER = 0x989AEb4d175e16225E39E87d0D97A3360524AD80;
    
    mapping(address => mapping(address => uint)) public claims_per_gauge;
    mapping(address => mapping(address => uint)) public reward_per_gauge;
    mapping(address => mapping(address => uint)) public reward_per_token;
    mapping(address => mapping(address => uint)) public active_period;
    // @dev: used to track posted bribes in future periods
    mapping(uint => mapping(address => mapping(address => uint))) public scheduled_rewards;
    mapping(address => mapping(uint => mapping(address => mapping(address => uint)))) public user_scheduled_rewards;
    mapping(address => mapping(address => mapping(address => uint))) public last_user_claim;
    mapping(address => uint) public next_claim_time;
    // @dev: Default 0x0 allows any account to claim for bribee. If set, blocks claims from arbitrary accounts.
    mapping(address => address) public claim_delegate;
    
    mapping(address => address[]) public _rewards_per_gauge;
    mapping(address => address[]) public _gauges_per_reward;
    mapping(address => mapping(address => bool)) public _rewards_in_gauge;

    address public owner = 0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52;
    address public fee_recipient = 0x93A62dA5a14C80f265DAbC077fCEE437B1a0Efde;
    address public pending_owner;
    uint public fee_percent = 1e16; // 1e16 is 1%; 1e18 is 100%
    mapping(address => address) public reward_recipient;
    
    /// @dev add reward/gauge pair if it hasn't been already
    function _add(address gauge, address reward) internal {
        if (!_rewards_in_gauge[gauge][reward]) {
            _rewards_per_gauge[gauge].push(reward);
            _gauges_per_reward[reward].push(gauge);
            _rewards_in_gauge[gauge][reward] = true;
            emit NewTokenReward(gauge, reward);
        }
    }
    
    function rewards_per_gauge(address gauge) external view returns (address[] memory) {
        return _rewards_per_gauge[gauge];
    }
    
    function gauges_per_reward(address reward) external view returns (address[] memory) {
        return _gauges_per_reward[reward];
    }
    
    /// @dev Required to sync each gauge/token pair to new week.
    /// @dev Can be triggered either by claiming or adding bribes to gauge/token pair.
    function _update_period(address gauge, address reward_token) internal returns (uint) {
        uint _period = active_period[gauge][reward_token];
        if (block.timestamp >= _period + WEEK) {
            _period = current_period();
            GAUGE.checkpoint_gauge(gauge);
            uint _bias = GAUGE.points_weight(gauge, _period).bias;
            uint last_user_vote = GAUGE.last_user_vote(BLOCKED_USER, gauge);
            uint omitted_bias;
            // @dev: Skip bias omission in edge-case where blocked user votes active period prior to _update_period called
            if(last_user_vote < _period) {
                omitted_bias = get_omitted_bias(gauge);
                _bias -= omitted_bias;
            }
            uint scheduled_amount = scheduled_rewards[_period][gauge][reward_token];
            if (scheduled_amount != 0) {
                delete scheduled_rewards[_period][gauge][reward_token]; // @dev: gas refund
            }
            reward_per_gauge[gauge][reward_token] += scheduled_amount;
            uint _amount = _max_claim(gauge, reward_token);
            if (_bias > 0){
                _amount = _amount * PRECISION / _bias;
                reward_per_token[gauge][reward_token] = _amount;
            }
            emit PeriodUpdated(gauge, _period, _amount, _bias, omitted_bias);
            active_period[gauge][reward_token] = _period;
        }
        return _period;
    }
    
    /// @notice Add single reward to the upcoming period
    /// @param gauge gauge to add reward to
    /// @param reward_token token address of reward to offer
    /// @param amount amount of tokens to offer as bribe in upcoming period
    function add_reward_amount(address gauge, address reward_token, uint amount) external returns (bool) {
        require(GAUGE.gauge_types(gauge) >= 0); // @dev: reverts on invalid gauge
        _safeTransferFrom(reward_token, msg.sender, address(this), amount);
        uint fee_take = fee_percent * amount / PRECISION;
        uint reward_amount = amount - fee_take;
        if (fee_take > 0){
            _safeTransfer(reward_token, fee_recipient, fee_take);
        }
        uint curr_period = _update_period(gauge, reward_token);
        _schedule_for_period(curr_period + WEEK, curr_period, gauge, reward_token, reward_amount, fee_take);
        return true;
    }

    /// @notice Schedule rewards for release in a specific range of future periods
    /// @dev When scheduling, specify index range where index of 0 is the upcoming period.
    /// @param gauge Gauge to add rewards to
    /// @param reward_token Token address of reward to offer
    /// @param amount_per_period Amount of tokens to offer per period
    /// @param n_periods Number of periods to bribe for. Will be applied to n number of periods beginning with the start period specified by delay.
    /// @param delay Number of periods after upcoming period from which to start scheduled rewards. 0 starts in upcoming period; 5 starts five weeks after upcoming period.
    function schedule_reward_amount(address gauge, address reward_token, uint amount_per_period, uint n_periods, uint delay) external returns (bool) {
        require(GAUGE.gauge_types(gauge) >= 0); // @dev: reverts on invalid gauge
        require(delay <= 20); // @dev: max 20 weeks
        require(n_periods <= 20); // @dev: max 20 weeks
        // Transfer tokens before updating state variables to prevent re-entry
        uint total_amount = n_periods * amount_per_period;
        _safeTransferFrom(reward_token, msg.sender, address(this), total_amount);
        uint total_fee_take = fee_percent * total_amount / PRECISION;
        uint fee_per;
        if (total_fee_take > 0){
            fee_per = total_fee_take / n_periods;
            // @dev: adjust total to prevent rounding mismatch
            total_fee_take = fee_per * n_periods;
            _safeTransfer(reward_token, fee_recipient, total_fee_take);
        }
        amount_per_period -= fee_per;
        uint curr_period = _update_period(gauge, reward_token);
        uint iterator_max = n_periods + delay;
        for (uint i = delay; i < iterator_max; i++){
            uint scheduled_period = curr_period + (i * WEEK) + WEEK;
            _schedule_for_period(scheduled_period, curr_period, gauge, reward_token, amount_per_period, fee_per);
        }
        emit RewardScheduled(msg.sender, curr_period, gauge, reward_token, total_amount - total_fee_take, total_fee_take, n_periods, delay);
        return true;
    }

    function _schedule_for_period(uint scheduled_period, uint curr_period, address gauge, address reward_token, uint reward_amount, uint fee_take) internal {
        // @dev: if posted in active period, apply to upcoming period. Otherwise, schedule for future period.
        if (scheduled_period == curr_period + WEEK) {
            reward_per_gauge[gauge][reward_token] += reward_amount;
        }
        else {
            scheduled_rewards[scheduled_period][gauge][reward_token] += reward_amount;
            user_scheduled_rewards[msg.sender][scheduled_period][gauge][reward_token] += reward_amount;
        }
        _add(gauge, reward_token);
        emit RewardAdded(msg.sender, scheduled_period, gauge, reward_token, reward_amount, fee_take);
    }

    /// @notice Allow briber to reclaim a bribe posted to a week that never got recognized in a week
    /// @dev If a bribe was posted using the schedule feature and receieves no claims/adds in the preceding week, the scheduled amount will fail to be included as a bribe. 
    /// @dev In this circumstance, the briber who scheduled the amount can use this function to recoup the amount. Else, the tokens will remain in the contract without utility.
    function retrieve_for_period(uint scheduled_period, address gauge, address reward_token) external {
        require(scheduled_period < current_period(), "!Past");
        uint amount = user_scheduled_rewards[msg.sender][scheduled_period][gauge][reward_token];
        if(amount > 0) {
            scheduled_rewards[scheduled_period][gauge][reward_token] -= amount;
            delete user_scheduled_rewards[msg.sender][scheduled_period][gauge][reward_token];
            _safeTransfer(reward_token, msg.sender, amount);
            emit RewardRetrieved(msg.sender, gauge, reward_token, scheduled_period, amount);
        }
    }

    /// @notice Helper function to help a user query if they're able to retreive a past bribe they posted for any given period.
    /// @dev If a bribe was posted using the schedule feature and receieves no claims/adds in the preceding week, the scheduled amount will fail to be included as a bribe. 
    /// @dev In this circumstance, the briber who scheduled the amount can use this helper to see how many tokens they can recover.
    function can_retrieve_for_period(uint scheduled_period, address gauge, address reward_token) external view returns (uint) {
        if (scheduled_period >= current_period()) {
            return 0;
        }
        return user_scheduled_rewards[msg.sender][scheduled_period][gauge][reward_token];
    }

    /// @notice Estimate pending bribe amount for any user
    /// @dev This function returns zero if active_period has not yet been updated.
    /// @dev Should not rely on this function for any user case where precision is required.
    function claimable(address user, address gauge, address reward_token) external view returns (uint) {
        uint _period = current_period();
        if(user == BLOCKED_USER || next_claim_time[user] > _period) {
            return 0;
        }
        if (last_user_claim[user][gauge][reward_token] >= _period) {
            return 0;
        }
        uint last_user_vote = GAUGE.last_user_vote(user, gauge);
        if (last_user_vote >= _period) {
            return 0;
        }
        if (_period != active_period[gauge][reward_token]) {
            return 0;
        }
        GaugeController.VotedSlope memory vs = GAUGE.vote_user_slopes(user, gauge);
        uint _user_bias = _calc_bias(vs.slope, vs.end);
        return _user_bias * reward_per_token[gauge][reward_token] / PRECISION;
    }

    function claim_reward(address gauge, address reward_token) external returns (uint) {
        return _claim_reward(msg.sender, gauge, reward_token);
    }

    function claim_reward_for_many(address[] calldata _users, address[] calldata _gauges, address[] calldata _reward_tokens) external returns (uint[] memory amounts) {
        require(_users.length == _gauges.length && _users.length == _reward_tokens.length, "!lengths");
        uint length = _users.length;
        amounts = new uint[](length);
        for (uint i = 0; i < length; i++) {
            amounts[i] = _claim_reward(_users[i], _gauges[i], _reward_tokens[i]);
        }
        return amounts;
    }

    function claim_reward_for(address user, address gauge, address reward_token) external returns (uint) {
        return _claim_reward(user, gauge, reward_token);
    }
    
    function _claim_reward(address user, address gauge, address reward_token) internal returns (uint) {
        bool permitted = msg.sender == user || (claim_delegate[user] == address(0) || claim_delegate[user] == msg.sender);
        if(!permitted || user == BLOCKED_USER || next_claim_time[user] > current_period()){
            return 0;
        }
        uint _period = _update_period(gauge, reward_token);
        uint _amount = 0;
        if (last_user_claim[user][gauge][reward_token] < _period) {
            last_user_claim[user][gauge][reward_token] = _period;
            if (GAUGE.last_user_vote(user, gauge) < _period) {
                GaugeController.VotedSlope memory vs = GAUGE.vote_user_slopes(user, gauge);
                uint _user_bias = _calc_bias(vs.slope, vs.end);
                _amount = _user_bias * reward_per_token[gauge][reward_token] / PRECISION;
                _amount = _min(_amount, _max_claim(gauge, reward_token));
                if (_amount > 0) {
                    claims_per_gauge[gauge][reward_token] += _amount;
                    address recipient = reward_recipient[user];
                    recipient = recipient == address(0) ? user : recipient;
                    _safeTransfer(reward_token, recipient, _amount);
                    emit RewardClaimed(user, gauge, reward_token, _amount);
                }
            }
        }
        return _amount;
    }

    /// @dev Compute bias from slope and lock end
    /// @param _slope User's slope
    /// @param _end Timestamp of user's lock end
    function _calc_bias(uint _slope, uint _end) internal view returns (uint) {
        uint current = current_period();
        if (current + WEEK >= _end) return 0;
        return _slope * (_end - current);
    }

    /// @dev Find total bias to omit on particular gauge.
    function get_omitted_bias(address gauge) public view returns (uint) {
        GaugeController.VotedSlope memory vs = GAUGE.vote_user_slopes(BLOCKED_USER, gauge);
        return _calc_bias(vs.slope, vs.end);
    }

    /// @dev Returns maximum claim amount for any gauge in current period
    function _max_claim(address gauge, address reward_token) internal view returns (uint) {
        return (
            reward_per_gauge[gauge][reward_token] -
            claims_per_gauge[gauge][reward_token]
        );
    }

    /// @dev Helper function to determine current period globally. Not specific to any gauges or internal state.
    function current_period() public view returns (uint) {
        return block.timestamp / WEEK * WEEK;
    }

    /// @notice Allow any user to route claimed rewards to a specified recipient address
    function set_recipient(address _recipient) external {
        require (_recipient != msg.sender, "self");
        require (_recipient != address(0), "0x0");
        address current_recipient = reward_recipient[msg.sender];
        require (_recipient != current_recipient, "Already set");
        
        // Update delegation mapping
        reward_recipient[msg.sender] = _recipient;
        
        if (current_recipient != address(0)) {
            emit ClearRewardRecipient(msg.sender, current_recipient);
        }

        emit SetRewardRecipient(msg.sender, _recipient);
    }

    /// @notice Allow any user to clear any previously specified reward recipient
    function clear_recipient() external {
        address current_recipient = reward_recipient[msg.sender];
        require (current_recipient != address(0), "No recipient set");
        reward_recipient[msg.sender]= address(0);
        emit ClearRewardRecipient(msg.sender, current_recipient);
    }

    /// @notice Allow owner to set fees of up to 4% of bribes upon deposit
    function set_fee_percent(uint _percent) external {
        require(msg.sender == owner, "!owner");
        require(_percent <= 4e16); // @dev: max 4%
        fee_percent = _percent;
        emit FeeUpdated(_percent);
    }

    function set_fee_recipient(address _recipient) external {
        require(msg.sender == owner, "!owner");
        fee_recipient = _recipient;
        emit SetFeeRecipient(_recipient);
    }

    /// @notice Allow to set a claim delegate, effectively blocking others from claiming rewards
    function set_claim_delegate(address _delegate) external {
        require (_delegate != msg.sender, "self");
        require (_delegate != address(0), "Clear First");
        address current_delegate = claim_delegate[msg.sender];
        require (_delegate != current_delegate, "Already set");
        
        // Update delegation mapping
        claim_delegate[msg.sender] = _delegate;
        
        if (current_delegate != address(0)) {
            emit ClearClaimDelegate(msg.sender, current_delegate);
        }

        emit SetClaimDelegate(msg.sender, _delegate);
    }

    function clear_claim_delegate() external {
        address current_delegate = claim_delegate[msg.sender];
        require (current_delegate != address(0), "No delegate set");
        claim_delegate[msg.sender]= address(0);
        emit ClearClaimDelegate(msg.sender, current_delegate);
    }

    function set_owner(address _new_owner) external {
        require(msg.sender == owner, "!owner");
        pending_owner = _new_owner;
    }

    function accept_owner() external {
        address _pending_owner = pending_owner;
        require(msg.sender == _pending_owner, "!pending_owner");
        owner = _pending_owner;
        emit ChangeOwner(_pending_owner);
        pending_owner = address(0);
    }

    function _safeTransfer(
        address token,
        address to,
        uint value
    ) internal {
        (bool success, bytes memory data) =
            token.call(abi.encodeWithSelector(erc20.transfer.selector, to, value));
        require(success && (data.length == 0 || abi.decode(data, (bool))));
    }
    
    function _safeTransferFrom(
        address token,
        address from,
        address to,
        uint value
    ) internal {
        (bool success, bytes memory data) =
            token.call(abi.encodeWithSelector(erc20.transferFrom.selector, from, to, value));
        require(success && (data.length == 0 || abi.decode(data, (bool))));
    }

    function _min(uint a, uint b) internal pure returns (uint) {
        return a < b ? a : b;
    }
}