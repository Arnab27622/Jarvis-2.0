from assistant.interface.commands import normalize_command

def test_normalize_command():
    # Test lowercase and punctuation stripping
    assert normalize_command("Hello World!") == "hello world"
    assert normalize_command("What's up?") == "what's up"
    
    # Test wake word removal
    assert normalize_command("Jarvis, what is the time?") == "what is the time"
    assert normalize_command("hey jarvis, play music") == "play music"
    
    # Test filler word removal
    assert normalize_command("please open youtube") == "open youtube"
    assert normalize_command("could you mind opening youtube please") == "mind opening youtube"
    assert normalize_command("can you tell me a joke") == "tell me a joke"
    
    # Combined test
    assert normalize_command("Okay Jarvis, could you please tell me the weather?") == "tell me the weather"
