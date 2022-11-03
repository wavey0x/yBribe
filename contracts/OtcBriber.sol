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

contract OtcBriber{

    struct BribeOffer{
        address briber; // slot one
        uint96 requiredVeCrvAmount; // max 7bil
        
        address gauge; //slot 2

        address bribeToken; // slot 3
        uint96 bribeId;
        
        uint168 weeklyBribeAmount; // slot 4
        uint40 start; // max 34000 years in the future
        uint8 numberOfWeeks;
        uint40 claimed; // we dont use bit 1, so max 39 usable bits

    }

    event SetRewardRecipient(address indexed user, address recipient);
    event ClearRewardRecipient(address indexed user, address recipient);
    event NewBribeOffer(address indexed briber, address indexed gauge, uint indexed start, uint numWeeks, uint id, uint requiredVeCrvAmount, address bribeToken, uint weeklyBribeAmount);
    event BribeClaimed(address indexed briber, address indexed gauge, uint indexed claimPeriod, uint id, uint votedVeCrvAmount, uint requiredVeCrvAmount, address bribeToken, uint weeklyBribeAmount);
    event BribeRetrieved(address indexed briber, address indexed gauge, uint indexed claimPeriod, uint id, uint requiredVeCrvAmount, address bribeToken, uint weeklyBribeAmount);

    
    mapping (uint256 => BribeOffer) public bribeOffers;
    address public rewardRecipient;
    uint96 public nextId;
    GaugeController constant GAUGE = GaugeController(0x2F50D538606Fa9EDD2B11E2446BEb18C9D5846bB);
    uint constant WEEK = 86400 * 7;
    address constant YEARN = 0xF147b8125d2ef93FB6965Db97D6746952a133934; // yearns crv locker and voter

    function setupBribe(address _gauge, address _bribeToken, uint168 _weeklyBribeAmount, uint96 _requiredVeCrvAmount, uint8 _numberOfWeeks, uint40 _start) external returns (uint96){
        return _setupBribe(_gauge,  _bribeToken,  _weeklyBribeAmount,  _requiredVeCrvAmount,  _numberOfWeeks,  _start);
    }
    function setupBribe(address _gauge, address _bribeToken, uint168 _weeklyBribeAmount, uint96 _requiredVeCrvAmount, uint8 _numberOfWeeks) external returns (uint96){
        return _setupBribe(_gauge,  _bribeToken,  _weeklyBribeAmount,  _requiredVeCrvAmount,  _numberOfWeeks, uint40(current_period() + WEEK));
    }

    function _setupBribe(address _gauge, address _bribeToken, uint168 _weeklyBribeAmount, uint96 _requiredVeCrvAmount, uint8 _numberOfWeeks, uint40 _start) internal returns (uint96 id) {
        id = nextId;
        nextId = id + 1;

        require(_start < block.timestamp + WEEK*52); // @dev: start date over a year in the future
        require(GAUGE.gauge_types(_gauge) >= 0); // @dev: reverts on invalid gauge
        require(_numberOfWeeks <= 39, "cant vote for more than 39");

        _safeTransferFrom(_bribeToken, msg.sender, address(this), uint256(_weeklyBribeAmount) * uint256(_numberOfWeeks));
        
        bribeOffers[id] = BribeOffer(
            msg.sender, _requiredVeCrvAmount, _gauge, _bribeToken, id, _weeklyBribeAmount, _start, _numberOfWeeks, 0 
        );

        emit NewBribeOffer(msg.sender, _gauge, _start, _numberOfWeeks, id,  _requiredVeCrvAmount, _bribeToken, _weeklyBribeAmount);

    }

    function set_recipient(address _recipient) external {
        require (_recipient != msg.sender, "self");
        require (msg.sender == YEARN, "not yearn");
        address currentRecipient = rewardRecipient;
        require (_recipient != currentRecipient, "Already set");
        
        // Update delegation mapping
        rewardRecipient = _recipient;
        
        if (currentRecipient != address(0)) {
            emit ClearRewardRecipient(msg.sender, currentRecipient);
        }
        if (rewardRecipient != address(0)) {
            emit SetRewardRecipient(msg.sender, rewardRecipient);
        }
    }

    function claimBribe(uint256 id, uint256 week) external {
        require(bribeExists(id), "bribe doesnt exist");

        BribeOffer memory _offer = bribeOffers[id];

        uint _bias = _claimable(_offer, week);

        require(_bias != 0, "not claimable");

        address recipient = rewardRecipient;
        recipient = recipient == address(0) ? YEARN : recipient;

        _safeTransfer(_offer.bribeToken, recipient, _offer.weeklyBribeAmount);
        uint256 claimingPeriod = _offer.start + ((week-1) * WEEK);

        emit BribeClaimed(_offer.briber, _offer.gauge, claimingPeriod, id, _bias, _offer.requiredVeCrvAmount, _offer.bribeToken, _offer.weeklyBribeAmount);

        _updateClaimed(week, _offer, id);
        
    }

    function retrieveUnclaimedBribesPerWeek(uint256 id, uint256 week) external{
        require(bribeExists(id), "bribe doesnt exist");

        BribeOffer memory _offer = bribeOffers[id];
        require(msg.sender == _offer.briber, "not your bribe");

        require(week <= _offer.numberOfWeeks, "too many weeks");

        uint256 claimingPeriod = _offer.start + ((week-1) * WEEK);

        require( !_hasClaimed(_offer.claimed, week), "already claimed for this week" ); //bitwise and

        bool canRetrieve = false;
        uint lastYearnVote = GAUGE.last_user_vote(YEARN, _offer.gauge);
        if(lastYearnVote > claimingPeriod){
            canRetrieve = true;
        }

        uint _bias = _votedAmount( _offer.gauge, lastYearnVote);
        if(_bias < _offer.requiredVeCrvAmount){
            canRetrieve = true;
        }

        require(canRetrieve || block.timestamp > claimingPeriod +  WEEK*4, "too close to claiming period" );

        _safeTransfer(_offer.bribeToken, msg.sender, _offer.weeklyBribeAmount);

        emit BribeRetrieved(_offer.briber, _offer.gauge, claimingPeriod, id, _offer.requiredVeCrvAmount, _offer.bribeToken, _offer.weeklyBribeAmount);

        _updateClaimed(week, _offer, id);
    }

    function hasClaimed(uint id, uint week) external view returns (bool){

        return _hasClaimed(bribeOffers[id].claimed, week);

    }
    function _hasClaimed(uint40 claimed, uint week) internal view returns (bool){
       
        uint40 claimBitmap = uint40(2**week);

        return claimed & claimBitmap != 0;
    }


    function retrievable(uint id) public view returns (bool){

        BribeOffer memory _offer = bribeOffers[id];

        if(!bribeExists(id)){
            return false;
        }

        uint endPeriod = _offer.start + WEEK*(_offer.numberOfWeeks-1);

        return block.timestamp > endPeriod +  WEEK*4;

    }

    function retrieveAll(uint256 id) external{
        require(retrievable(id));

        BribeOffer memory _offer = bribeOffers[id];
        require(msg.sender == _offer.briber, "not your bribe");

        for(uint i = 1; i < _offer.numberOfWeeks; i++){
            if(!_hasClaimed(_offer.claimed, i)){
                uint256 claimingPeriod = _offer.start + ((i-1) * WEEK);
                _safeTransfer(_offer.bribeToken, msg.sender, _offer.weeklyBribeAmount);
                emit BribeRetrieved(_offer.briber, _offer.gauge, claimingPeriod, id, _offer.requiredVeCrvAmount, _offer.bribeToken, _offer.weeklyBribeAmount);

            }
        }
        delete bribeOffers[id];
        
    }


    function claimable(uint id, uint week) external view returns (bool){

        BribeOffer memory _offer = bribeOffers[id];

        return _claimable(_offer, week) > 0;

    }

    function _claimable(BribeOffer memory _offer, uint week) internal view returns (uint){

        if(!bribeExists(_offer.bribeId)){
            return 0;
        }

        if(week > _offer.numberOfWeeks){
            return 0;
        }

        uint256 claimingPeriod = _offer.start + ((week-1) * WEEK);
        
        if(claimingPeriod > block.timestamp){
            return 0;
        }
        

        if(_hasClaimed(_offer.claimed, week)){
            return 0;
        }

        uint lastYearnVote = GAUGE.last_user_vote(YEARN, _offer.gauge);
        if(lastYearnVote >= claimingPeriod){
            return 0;
        }

        uint _bias = _votedAmount(_offer.gauge, lastYearnVote);

        if(_bias < _offer.requiredVeCrvAmount){
            return 0;
        }else{
            return _bias;
        }

    }

    function votedAmount(address _gauge) external view returns (uint){

        uint lastYearnVote = GAUGE.last_user_vote(YEARN, _gauge);

        return _votedAmount( _gauge,  lastYearnVote);


    }

    function _votedAmount(address _gauge, uint lastYearnVote) internal view returns (uint){

        GaugeController.VotedSlope memory vs = GAUGE.vote_user_slopes(YEARN, _gauge);
        return _calc_bias(vs.slope, vs.end, lastYearnVote);


    }

    function _updateClaimed(uint256 week, BribeOffer memory _offer, uint256 id) internal {

        uint40 totalClaimed = _offer.claimed + uint40(2**week); //binary notation tracking weeks starting at index 1
        if (totalClaimed == 2**uint40(_offer.numberOfWeeks) *2 -2){
            //all claimed. delete
            delete bribeOffers[id];

        }else{
            bribeOffers[id].claimed = totalClaimed;
        }
    }

    


    function _calc_bias(uint _slope, uint _end, uint256 current) internal view returns (uint) {
        if (current + WEEK >= _end) return 0;
        return _slope * (_end - current);
    }


    function current_period() public view returns (uint) {
        return block.timestamp / WEEK * WEEK;
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

    function bribeExists(uint id) public view returns(bool){
        return bribeOffers[id].briber != address(0) ;
        
    }

    

}