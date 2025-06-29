// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title Escrow
 * @dev Simple Escrow contract for buyer and seller with manual release
 */
contract Escrow {
    address public buyer;
    address public seller;
    uint256 public amount;
    bool public isReleased;
    bool public isRefunded;

    constructor(address _buyer, address _seller) payable {
        require(msg.value > 0, "Must send MATIC to escrow");
        buyer = _buyer;
        seller = _seller;
        amount = msg.value;
        isReleased = false;
        isRefunded = false;
    }

    modifier onlyBuyer() {
        require(msg.sender == buyer, "Only buyer can perform this action");
        _;
    }

    modifier onlySeller() {
        require(msg.sender == seller, "Only seller can perform this action");
        _;
    }

    modifier notCompleted() {
        require(!isReleased && !isRefunded, "Escrow already completed");
        _;
    }

    function releaseToSeller() external onlyBuyer notCompleted {
        isReleased = true;
        payable(seller).transfer(amount);
    }

    function refundToBuyer() external onlySeller notCompleted {
        isRefunded = true;
        payable(buyer).transfer(amount);
    }

    function getBalance() external view returns (uint256) {
        return address(this).balance;
    }
}

