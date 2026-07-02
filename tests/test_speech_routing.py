import os
import sys
import unittest
from unittest.mock import patch

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from assistant.core.llm_utils import clean_for_speech
from assistant.core.llm_manager import LLMManager
from assistant.core.tools import get_current_location
from assistant.automation.features.utility_automation import handle_brightness

class TestSpeechAndRouting(unittest.TestCase):
    def test_speech_normalization(self):
        # 1. Test case-sensitive country code mapping
        self.assertEqual(clean_for_speech("in"), "in")
        self.assertEqual(clean_for_speech("IN"), "India")
        self.assertEqual(clean_for_speech("US"), "United States")
        self.assertEqual(clean_for_speech("GB"), "United Kingdom")
        self.assertEqual(clean_for_speech("Delhi, IN"), "Delhi, India")

        # 2. Test AI pronunciation mapping
        self.assertEqual(clean_for_speech("AI"), "A I")
        self.assertEqual(clean_for_speech("ai"), "A I")

        # 3. Test millisecond unit space removal
        self.assertEqual(clean_for_speech("10ms"), "10 milliseconds")
        self.assertEqual(clean_for_speech("10 ms"), "10 milliseconds")
        self.assertEqual(clean_for_speech("1 ms"), "1 millisecond")

        # 4. Test misspelled miliseconds correction
        self.assertEqual(clean_for_speech("10 miliseconds"), "10 milliseconds")
        self.assertEqual(clean_for_speech("1 milisecond"), "1 millisecond")

        # 5. Test min/mins expansion
        self.assertEqual(clean_for_speech("10 mins"), "10 minutes")
        self.assertEqual(clean_for_speech("1 min"), "1 minute")
        self.assertEqual(clean_for_speech("wait a min"), "wait a minute")

    def test_intent_routing(self):
        llm = LLMManager()
        
        # Test routing of playlist and music actions
        self.assertEqual(llm._identify_intent("Can you put on a background playlist that helps with concentration?"), "tools")
        self.assertEqual(llm._identify_intent("play some music for study"), "tools")
        
        # Test routing of memory / Wi-Fi password actions
        self.assertEqual(llm._identify_intent("Just so you know, my new guest WIFI password is 'BeOurGuest123'"), "tools")
        self.assertEqual(llm._identify_intent("What did I set that guest network password to again?"), "tools")
        
        # Test routing of break / stretch reminder actions
        self.assertEqual(llm._identify_intent("my back is starting to hurt. can you make sure I take a break and stretch in about half an hour?"), "tools")
        
        # Test location actions
        self.assertEqual(llm._identify_intent("what's my current location"), "tools")
        self.assertEqual(llm._identify_intent("where am i"), "tools")
        
        # Test battery & system status actions
        self.assertEqual(llm._identify_intent("check battery"), "tools")
        self.assertEqual(llm._identify_intent("what is the battery status"), "tools")

    @patch("screen_brightness_control.set_brightness")
    def test_handle_brightness(self, mock_set_brightness):
        # Test digit brightness parsing
        handle_brightness("change brightness to 50")
        mock_set_brightness.assert_called_with(50)
        
        # Test word brightness parsing
        handle_brightness("change brightness to fifty")
        mock_set_brightness.assert_called_with(50)
        
        # Test word brightness parsing for hundred
        handle_brightness("set brightness to hundred")
        mock_set_brightness.assert_called_with(100)

    @patch("assistant.automation.integrations.check_weather.get_location")
    @patch("assistant.automation.integrations.check_weather._fetch_weather_data")
    def test_get_current_location(self, mock_fetch_weather, mock_get_location):
        # 1. Test case when geocoder already returns city & country
        mock_get_location.return_value = {
            "latitude": 22.57, "longitude": 88.36, "city": "Kolkata", "country": "India"
        }
        res = get_current_location()
        self.assertIn("Kolkata", res)
        self.assertIn("India", res)
        mock_fetch_weather.assert_not_called()

        # 2. Test fallback reverse-geocoding via OpenWeatherMap API
        mock_get_location.return_value = {
            "latitude": 22.57, "longitude": 88.36, "city": "", "country": ""
        }
        mock_fetch_weather.return_value = {
            "name": "Kolkata",
            "sys": {"country": "IN"}
        }
        res = get_current_location()
        self.assertIn("Kolkata", res)
        self.assertIn("IN", res)
        mock_fetch_weather.assert_called_with(lat=22.57, lon=88.36)

if __name__ == "__main__":
    import os
    try:
        unittest.main(exit=False)
    finally:
        # Force exit to prevent background Kokoro scheduler thread from hanging the process
        os._exit(0)
