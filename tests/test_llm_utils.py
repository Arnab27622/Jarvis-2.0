from assistant.core.llm_utils import (
    clean_llm_output,
    normalize_for_tts,
    clean_for_speech,
    split_sentences,
    trim_history
)

def test_clean_llm_output():
    # Test latex removal
    text = r"The value is $\approx$ 5 \times 10."
    clean = clean_llm_output(text)
    assert "approximately" in clean
    assert "times" in clean
    assert "$" not in clean

def test_normalize_for_tts():
    # Test negative numbers and decimals
    assert normalize_for_tts("-5.5") == "-5 point 5"

    # Test units
    assert normalize_for_tts("50 kg") == "50 kilograms"

    # Test temperature
    assert normalize_for_tts("20 °C") == "20 degrees Celsius"

    # Test chemical formulas
    assert normalize_for_tts("H2O") == "H 2 O"
    assert normalize_for_tts("CO2") == "C O 2"

    # Test fractions
    assert normalize_for_tts("1/2") == "one half"
    assert normalize_for_tts("3/4") == "three quarters"

def test_clean_for_speech():
    # Ensure code blocks are removed
    text = "Here is the function: ```python\ndef foo(): pass\n``` It is good."
    clean = clean_for_speech(text)
    assert "def foo" not in clean
    assert "Here is the function" in clean
    assert "It is good" in clean

def test_split_sentences():
    text = "Hello there. How are you? I am fine!"
    sentences = split_sentences(text)
    assert sentences[0].strip() == "Hello there."
    assert sentences[1].strip() == "How are you?"
    assert sentences[2].strip() == "I am fine!"

def test_trim_history():
    history = [{"role": "system", "content": "You are a bot"}]
    for i in range(15):
        history.append({"role": "user", "content": f"msg {i}"})
    
    trimmed = trim_history(history, max_messages=10)
    assert len(trimmed) == 11 # 1 system + 10 messages
    assert trimmed[0]["role"] == "system"
    assert trimmed[1]["content"] == "msg 5"
    assert trimmed[-1]["content"] == "msg 14"
