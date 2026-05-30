import pytest
from assistant.core.registry import CommandRegistry

def test_keyword_registry():
    registry = CommandRegistry()
    called = []
    
    def handler_foo(text):
        called.append("foo")
        
    registry.register_keyword(["apple", "banana"], handler_foo)
    
    # Should match
    assert registry.execute("I like apple pie") == True
    assert "foo" in called
    
    # Should not match
    called.clear()
    assert registry.execute("I like orange juice") == False
    assert len(called) == 0

def test_regex_registry():
    registry = CommandRegistry()
    called = {}
    
    def handler_bar(city):
        called["city"] = city
        
    # Using named group
    registry.register_regex(r"weather in (?P<city>[a-zA-Z]+)", handler_bar)
    
    assert registry.execute("what is the weather in London today?") == True
    assert called.get("city") == "London"

def test_fuzzy_registry():
    registry = CommandRegistry()
    called = []
    
    def handler_baz(text):
        called.append("baz")
        
    registry.register_fuzzy(["play music", "start song"], handler_baz, score_cutoff=80)
    
    # Minor typo should still match
    assert registry.execute("play mucis") == True
    assert "baz" in called
    
    # Completely different shouldn't match
    called.clear()
    assert registry.execute("turn off the lights") == False
    assert len(called) == 0

def test_priority():
    registry = CommandRegistry()
    called = []
    
    def handler_low(text):
        called.append("low")
        
    def handler_high(text):
        called.append("high")
        
    registry.register_keyword(["test"], handler_low, priority=0)
    registry.register_keyword(["test"], handler_high, priority=10)
    
    registry.execute("this is a test")
    assert called == ["high"]
