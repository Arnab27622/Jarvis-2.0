import pytest
from unittest.mock import patch, AsyncMock
from assistant.core.llm_manager import LLMManager

@pytest.mark.asyncio
async def test_llm_routing():
    manager = LLMManager()
    
    # Mock the BaseAgent run methods instead of the legacy fallback chain
    with patch.object(manager.general, 'run', new_callable=AsyncMock) as mock_general, \
         patch.object(manager.vision, 'run', new_callable=AsyncMock) as mock_vision, \
         patch.object(manager.coder, 'run', new_callable=AsyncMock) as mock_coder, \
         patch.object(manager.researcher, 'run', new_callable=AsyncMock) as mock_researcher, \
         patch("assistant.core.speak_selector.speak_streaming"):
         
        mock_general.return_value = "General response"
        mock_vision.return_value = "Vision response"
        mock_coder.return_value = "Coder response"
        mock_researcher.return_value = "Researcher response"
        
        # Test General Routing
        response = await manager.get_response_async("Hello Jarvis")
        assert mock_general.called
        
        # Test Coder Routing
        response = await manager.get_response_async("Write a python script")
        assert mock_coder.called
        
        # Test Vision Routing
        response = await manager.get_response_async("What is on my screen?")
        assert mock_vision.called
        
        # Test Web Routing
        response = await manager.get_response_async("Search for latest news")
        assert mock_researcher.called

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
