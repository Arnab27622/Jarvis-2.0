import pytest
import datetime
from assistant.utils.time_parser import parse_time, parse_duration, parse_relative_time, parse_absolute_time

def test_parse_time():
    assert parse_time("5:30 pm") == (17, 30)
    assert parse_time("14:20") == (14, 20)
    assert parse_time("noon") == (12, 0)
    assert parse_time("midnight") == (0, 0)
    assert parse_time("3 am") == (3, 0)
    assert parse_time("0900") == (9, 0)

def test_parse_duration():
    assert parse_duration("in 1 hour") == 60
    assert parse_duration("30 minutes") == 30
    assert parse_duration("1.5 hours") == 90
    assert parse_duration("half an hour") == 30
    assert parse_duration("2 hours and 15 minutes") == 135

def test_parse_relative_time():
    target_time, message = parse_relative_time("remind me to call John in 30 minutes")
    assert target_time is not None
    assert "call john" in message

    target_time, message = parse_relative_time("set an alarm in 2 hours")
    assert target_time is not None
    assert message == "You have a reminder!"

def test_parse_absolute_time():
    target_time, message = parse_absolute_time("remind me to buy milk at 5 pm tomorrow", is_reminder=True)
    assert target_time is not None
    assert target_time.hour == 17
    assert target_time.minute == 0
    assert "buy milk" in message
