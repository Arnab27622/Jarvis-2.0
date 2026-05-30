import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from assistant.core.llm_manager import LLMManager

@pytest.mark.asyncio
async def test_llm_fallback_chain():
    manager = LLMManager()
    
    # Mock all the actual LLM calls
    with patch.object(manager, '_call_huggingface', new_callable=AsyncMock) as mock_hf, \
         patch.object(manager, '_call_gemini_tools', new_callable=AsyncMock) as mock_gemini_tools, \
         patch.object(manager, '_call_gemini_streaming', new_callable=AsyncMock) as mock_gemini_stream, \
         patch.object(manager, '_call_openrouter', new_callable=AsyncMock) as mock_openrouter, \
         patch.object(manager, '_call_g4f', new_callable=AsyncMock) as mock_g4f, \
         patch("assistant.core.speak_selector.speak_streaming") as mock_speak:
         
        # Simulate primary failing, first fallback (Gemini Streaming) failing, second fallback (OpenRouter) succeeding
        mock_gemini_stream.return_value = None
        mock_hf.return_value = None
        mock_openrouter.return_value = "OpenRouter response"
        mock_g4f.return_value = None
        
        # Test fallback works
        response = await manager.get_response_async("Hello")
        
        # Ensure it tried the fallbacks
        assert mock_gemini_stream.called
        assert mock_openrouter.called
        assert "OpenRouter response" in response

@pytest.mark.asyncio
async def test_tts_queue_integration():
    from assistant.core.mouth import tts_queue
    from assistant.core.llm_utils import split_sentences
    
    # Test that sentence splitting correctly feeds the queue
    text = "Hello world. This is a test! Right?"
    sentences = split_sentences(text)
    
    # Just verify the logic of pushing to queue
    assert len(sentences) == 3
    for sentence in sentences:
        tts_queue.put((sentence, None, "test_id"))
        
    assert tts_queue.qsize() >= 3
    
    # Drain queue
    while not tts_queue.empty():
        tts_queue.get_nowait()
