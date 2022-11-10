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
}
interface IyBribe{
     function current_period() external view returns (uint);
     function get_omitted_bias(address gauge) external view returns (uint);
     function reward_per_gauge(address gauge, address reward) external view returns (uint);
     function claims_per_gauge(address gauge, address reward) external view returns (uint);
}

contract BribeHelper{

    IyBribe public yBribe;
    GaugeController constant gaugeController = GaugeController(0x2F50D538606Fa9EDD2B11E2446BEb18C9D5846bB);

    constructor(address _yBribe) {
        yBribe = IyBribe(_yBribe);
    }
    function getNewRewardPerToken(address gauge, address reward_token) external returns (uint){
        uint _period = yBribe.current_period() + 86400 * 7;
        gaugeController.checkpoint_gauge(gauge);
        uint _bias = gaugeController.points_weight(gauge, _period).bias;
        uint omitted_bias = yBribe.get_omitted_bias(gauge);
        _bias -= omitted_bias;
        uint _amount = yBribe.reward_per_gauge(gauge, reward_token) - yBribe.claims_per_gauge(gauge, reward_token);
        if (_bias > 0){
            return _amount * 10**18 / _bias;
        }else{
            return 0;
        }
    }
}