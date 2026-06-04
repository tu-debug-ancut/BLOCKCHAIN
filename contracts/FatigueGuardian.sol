// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract FatigueGuardian {

    struct HealthEvent {
        uint256 timestamp;
        string eventType;
        string message;
    }

    HealthEvent[] public events;

    event EventRecorded(
        uint256 timestamp,
        string eventType,
        string message
    );

    function addEvent(
        string memory _eventType,
        string memory _message
    ) public {
        events.push(
            HealthEvent(block.timestamp, _eventType, _message)
        );

        emit EventRecorded(block.timestamp, _eventType, _message);
    }

    function getTotalEvents() public view returns (uint256) {
        return events.length;
    }
}
