// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

/**
 * @title SimpleStorage
 * @dev A very basic contract to store and retrieve a number.
 */
contract SimpleStorage {
    uint256 private _value;

    event ValueChanged(address indexed sender, uint256 newValue);

    constructor(uint256 initialValue) {
        _value = initialValue;
        emit ValueChanged(msg.sender, initialValue);
    }

    function set(uint256 newValue) public {
        _value = newValue;
        emit ValueChanged(msg.sender, newValue);
    }

    function get() public view returns (uint256) {
        return _value;
    }
} 