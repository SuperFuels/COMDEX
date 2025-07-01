// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/// @title GLU Stablecoin (ERC20)
contract GLU is ERC20 {
    constructor(uint256 initialSupply) ERC20("GLU Stablecoin","GLU") {
        _mint(msg.sender, initialSupply);
    }
}
