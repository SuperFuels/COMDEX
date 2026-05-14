// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/// @title Escrow contract for GLU token
contract GLUEscrow {
    IERC20 public immutable token;
    address public immutable owner;
    struct Deposit { address depositor; address beneficiary; uint256 amount; bool released; }
    mapping(uint256 => Deposit) public deposits;
    uint256 public nextId;

    constructor(IERC20 _token) {
        token = _token;
        owner = msg.sender;
    }

    function createEscrow(address beneficiary, uint256 amount) external returns (uint256) {
        require(token.transferFrom(msg.sender, address(this), amount), "transfer failed");
        deposits[nextId] = Deposit(msg.sender, beneficiary, amount, false);
        return nextId++;
    }

    function release(uint256 id) external {
        Deposit storage d = deposits[id];
        require(!d.released, "already released");
        require(msg.sender == d.depositor || msg.sender == owner, "not authorized");
        d.released = true;
        require(token.transfer(d.beneficiary, d.amount), "transfer failed");
    }
}
