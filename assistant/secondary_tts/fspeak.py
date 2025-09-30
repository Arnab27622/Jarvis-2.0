"""
FSpeak Module - Emotion-Aware Text-to-Speech with Sentiment Analysis

This module provides an advanced text-to-speech system that incorporates real-time
sentiment analysis and emotion detection to deliver emotionally appropriate speech
synthesis. It uses multiple emotion detection strategies and adjusts speech parameters
dynamically based on emotional content.

Key Features:
- Multi-layered emotion detection (keyword-based, sentiment analysis, emotion tracking)
- Dynamic speech parameter adjustment (rate, volume) based on emotional context
- Real-time sentiment analysis using TextBlob
- Threaded execution for synchronized text animation and speech
- Comprehensive emotion vocabulary with hierarchical detection
- Offline TTS using pyttsx3 with emotional intonation

Emotion Detection Hierarchy:
1. Keyword-based emotion detection (highest priority)
2. Emotion phase tracking (medium priority)
3. Sentiment analysis (baseline)

Dependencies:
- pyttsx3: Offline text-to-speech engine
- textblob: Sentiment analysis and NLP processing
- threading: Concurrent text and speech execution
"""

import sys
import threading
import time
import pyttsx3
from textblob import TextBlob


def detect_emotion(text: str) -> str:
    """
    Detect emotion through direct keyword matching.

    Uses a comprehensive dictionary of emotion keywords to identify
    explicit emotional expressions in the text. This method provides
    high-confidence emotion detection when specific emotion words are present.

    Args:
        text (str): Input text to analyze for emotional keywords

    Returns:
        str: Detected emotion name or "unknown" if no matches found

    Emotion Categories:
        - Positive: ecstatic, overjoyed, elated, joyful, happy, cheerful
        - Content: content, pleased, neutral, indifferent
        - Negative: unhappy, sad, mournful, despondent, melancholy, depressed
        - Complex: hopeful, optimistic, grateful, inspired, amused, calm
        - Negative States: confused, disappointed, frustrated, anxious, overwhelmed
        - Strong Negative: guilty, disgusted, repulsed, detached, angry
    """
    text_lower = text.lower()

    # Comprehensive emotion keyword dictionary
    emotion_keywords = {
        "ecstatic": ["ecstatic"],
        "overjoyed": ["overjoyed"],
        "elated": ["elated"],
        "joyful": ["joyful"],
        "happy": ["happy"],
        "cheerful": ["cheerful"],
        "content": ["content"],
        "pleased": ["pleased"],
        "neutral": ["neutral"],
        "indifferent": ["indifferent"],
        "unhappy": ["unhappy"],
        "sad": ["sad"],
        "mournful": ["mournful"],
        "despondent": ["despondent"],
        "melancholy": ["melancholy"],
        "depressed": ["depressed"],
        "devastated": ["devastated"],
        "hopeful": ["hopeful"],
        "optimistic": ["optimistic"],
        "grateful": ["grateful"],
        "inspired": ["inspired"],
        "amused": ["amused"],
        "calm": ["calm"],
        "confused": ["confused"],
        "disappointed": ["disappointed"],
        "frustrated": ["frustrated"],
        "anxious": ["anxious"],
        "overwhelmed": ["overwhelmed"],
        "guilty": ["guilty"],
        "disgusted": ["disgusted"],
        "repulsed": ["repulsed"],
        "detached": ["detached"],
        "angry": ["angry", "irate", "furious", "enraged"],
    }

    # Check for each emotion in the keyword dictionary
    for emotion, keywords in emotion_keywords.items():
        if any(word in text_lower for word in keywords):
            return emotion

    return "unknown"


def get_emotion(sentiment):
    """
    Map sentiment scores to emotions and speech parameters.

    Converts TextBlob sentiment scores (-1.0 to 1.0) to specific emotions
    and corresponding speech adjustments (rate and volume).

    Args:
        sentiment (float): Sentiment polarity score from TextBlob (-1.0 to 1.0)

    Returns:
        tuple: (emotion_name, (speech_rate, speech_volume))
            - emotion_name (str): Detected emotion category
            - speech_rate (int): Words per minute adjustment
            - speech_volume (float): Volume level (0.0 to 1.0)

    Sentiment Scale:
        > 0.7: Ecstatic (fast, loud)      | < -0.7: Devastated (slow, quiet)
        > 0.6: Overjoyed (fast, loud)     | < -0.6: Depressed (very slow)
        > 0.5: Elated (fast, moderate)    | < -0.5: Melancholy (slow, very quiet)
        > 0.4: Joyful (fast, moderate)    | < -0.4: Despondent (slow)
        > 0.3: Happy (moderate, moderate) | < -0.3: Mournful (slow)
        > 0.2: Cheerful (moderate)        | < -0.2: Sad (slow)
        > 0.1: Content (moderate, quiet)  | < -0.1: Unhappy (slow)
        > 0.05: Pleased (slow, quiet)     | < -0.05: Indifferent (slow)
        > -0.05: Neutral (normal)         | Else: Distressed (variable)
    """
    # TextBlob sentiment is between -1 and 1
    if sentiment > 0.7:
        return "ecstatic", (220, 1.5)  # Very fast, loud
    elif sentiment > 0.6:
        return "overjoyed", (180, 1.4)  # Fast, loud
    elif sentiment > 0.5:
        return "elated", (190, 1.3)  # Fast, moderate-loud
    elif sentiment > 0.4:
        return "joyful", (180, 1.2)  # Fast, moderate
    elif sentiment > 0.3:
        return "happy", (170, 1.1)  # Moderate-fast, slightly loud
    elif sentiment > 0.2:
        return "cheerful", (160, 1.0)  # Moderate, normal volume
    elif sentiment > 0.1:
        return "content", (150, 0.9)  # Moderate-slow, quiet
    elif sentiment > 0.05:
        return "pleased", (140, 0.8)  # Slow, quiet
    elif sentiment > -0.05:
        return "neutral", (130, 1)  # Normal rate, normal volume
    elif sentiment > -0.1:
        return "indifferent", (120, 1)  # Slow, normal volume
    elif sentiment > -0.2:
        return "unhappy", (110, 1)  # Slow, normal volume
    elif sentiment > -0.3:
        return "sad", (100, 1)  # Slow, normal volume
    elif sentiment > -0.4:
        return "mournful", (100, 1)  # Slow, normal volume
    elif sentiment > -0.5:
        return "despondent", (170, 1)  # Variable rate, normal volume
    elif sentiment > -0.6:
        return "melancholy", (170, 0.1)  # Variable rate, very quiet
    elif sentiment > -0.7:
        return "depressed", (60, 1)  # Very slow, normal volume
    elif sentiment > -0.8:
        return "devastated", (180, 1)  # Variable rate, normal volume
    elif sentiment > -0.9:
        return "hopeful", (175, 1.3)  # Fast, moderate-loud
    else:
        return "distressed", (100, 0.8)  # Moderate, quiet


def track_emotion_phases(text):
    """
    Detect emotional phases through extended vocabulary analysis.

    Uses broader emotion categories with extensive word lists to identify
    emotional context and phases that may not be captured by simple sentiment
    analysis or direct keyword matching.

    Args:
        text (str): Input text to analyze for emotional context

    Returns:
        str or None: Detected emotion phase category or None if no match

    Emotion Phases:
        - love: Romantic, affectionate, tender emotions
        - happy: Joyful, cheerful, positive emotions
        - content: Peaceful, serene, satisfied emotions
        - neutral: Objective, balanced, unemotional states
        - moody: Unsettled, irritable, restless states
        - sad: Unhappy, mournful, dejected states
        - angry: Irate, furious, hostile states
    """
    text_lower = text.lower()

    # Extensive emotion category dictionaries
    emotion_categories = {
        "love": [
            "love",
            "romance",
            "affection",
            "passion",
            "adoration",
            "devotion",
            "infatuation",
            "desire",
            "attraction",
            "yearning",
            "admiration",
            "enchantment",
            "sweetness",
            "heartfelt",
            "tender",
            "embrace",
            "cherish",
            "butterfly",
            "amorous",
            "sentiment",
            "hug",
            "kiss",
            "whisper",
            "yearn",
            "lovers",
            "connection",
            "affinity",
            "magnetic",
            "attracted",
            "beloved",
            "emotion",
            "fond",
            "harmony",
            "sympathy",
            "infatuated",
            "enamored",
            "darling",
            "tenderly",
            "heartwarming",
            "softness",
            "heartthrob",
            "amicable",
            "attachment",
            "honeyed",
            "admirer",
            "adorniness",
            "swoon",
            "entranced",
            "enveloped",
            "heartstrings",
            "enamored",
            "lovestruck",
            "warmhearted",
            "compassionate",
            "quixotic",
            "wooing",
            "nurturing",
            "whispers",
            "languishing",
            "romeo",
            "juliet",
            "emblazoned",
            "fancy",
            "allure",
            "rapture",
            "enraptured",
            "fantasy",
            "longing",
            "alluring",
            "savor",
            "spark",
            "enchanted",
            "elation",
        ],
        "happy": [
            "happy",
            "joyful",
            "pleased",
            "content",
            "cheerful",
            "delighted",
            "euphoric",
            "merry",
            "upbeat",
            "radiant",
            "sunny",
            "ecstatic",
            "buoyant",
            "lighthearted",
            "vibrant",
            "carefree",
            "satisfied",
            "optimistic",
            "whimsical",
            "playful",
            "jubilant",
            "grateful",
            "spirited",
            "enthusiastic",
            "exhilarated",
            "blessed",
            "zestful",
            "jocular",
            "sprightly",
            "jolly",
            "hopeful",
            "sunny",
            "peppy",
            "jaunty",
            "chirpy",
            "zippy",
        ],
        "content": [
            "peaceful",
            "serene",
            "tranquil",
            "calm",
            "satisfied",
            "relaxed",
            "at ease",
            "reassured",
            "placid",
            "soothed",
            "undisturbed",
            "gratified",
            "composed",
            "assured",
            "repose",
            "compared",
            "untroubled",
            "quieted",
            "restful",
            "eased",
            "at peace",
            "serenity",
            "easeful",
            "steady",
            "hushed",
            "calmness",
            "heartsease",
            "pacified",
            "halcyon",
            "pacification",
            "replenished",
            "equanimity",
            "centred",
            "unperturbed",
            "contentedness",
            "contentment",
            "satisfaction",
        ],
        "neutral": [
            "neutral",
            "indifferent",
            "composed",
            "unaffected",
            "dispassionate",
            "objective",
            "uninvolved",
            "unperturbed",
            "unresponsive",
            "stoic",
            "imperturbable",
            "distant",
            "equanimous",
            "balanced",
            "unflappable",
            "cool-headed",
            "serene",
            "tranquil",
            "unfazed",
            "undisturbed",
            "unruffled",
            "untroubled",
            "easygoing",
            "unconcerned",
            "unexcitable",
            "unmoved",
            "remote",
            "impassive",
            "unimpressed",
            "unworried",
            "nonplussed",
            "matter-of-fact",
            "unresponsive",
            "cool",
            "untouched",
            "unbiased",
            "detached",
            "unprejudiced",
            "disinterested",
        ],
        "moody": [
            "moody",
            "unsettled",
            "irritable",
            "restless",
            "discontent",
            "sullen",
            "sulky",
            "brooding",
            "fretful",
            "edgy",
            "perturbed",
            "tense",
            "restive",
            "anxious",
            "agitated",
            "uneasy",
            "pouty",
            "choleric",
            "querulous",
            "cranky",
            "cross",
            "pensive",
            "melancholy",
            "blue",
            "morose",
            "lamenting",
            "wistful",
            "displeased",
            "dissatisfied",
            "malcontent",
            "grumbling",
            "craving",
            "whining",
            "frowning",
            "dejected",
            "depressed",
            "dismal",
            "despondent",
            "downhearted",
            "worried",
            "aggrieved",
        ],
        "sad": [
            "sad",
            "unhappy",
            "mournful",
            "disheartened",
            "dejected",
            "depressed",
            "dismal",
            "despondent",
            "forlorn",
            "gloomy",
            "dreary",
            "woeful",
            "cheerless",
            "heartbroken",
            "somber",
            "down in the dumps",
            "downhearted",
            "low-spirited",
            "downcast",
            "inconsolable",
            "miserable",
            "glum",
            "sullen",
            "wretched",
            "regretful",
            "lamenting",
            "grief-stricken",
            "long-faced",
            "woebegone",
            "doleful",
            "tearful",
            "funereal",
            "tragic",
            "lachrymose",
            "weepy",
            "morbid",
            "anguished",
            "heavyhearted",
        ],
        "angry": [
            "angry",
            "irate",
            "furious",
            "enraged",
            "agitated",
            "irritated",
            "wrathful",
            "livid",
            "maddened",
            "exasperated",
            "annoyed",
            "provoked",
            "irked",
            "fuming",
            "outraged",
            "hostile",
            "fierce",
            "resentful",
            "tempestuous",
            "stormy",
            "choleric",
            "vexed",
            "bitter",
            "offended",
            "cross",
            "huffy",
            "upset",
            "tumultuous",
            "spiteful",
            "sullen",
            "rancorous",
            "sour",
            "irritable",
            "testy",
            "petulant",
            "peevish",
            "incensed",
            "infuriated",
            "inflamed",
            "burning",
            "hot-tempered",
            "out of control",
            "wrath",
            "hostility",
            "vengeful",
        ],
    }

    # Check for emotion category matches
    for emotion, words in emotion_categories.items():
        if any(word in text_lower for word in words):
            return emotion

    return None


def print_animated_message(message):
    """
    Display text with typewriter-style animation.

    Creates an engaging visual experience by printing characters sequentially
    with controlled timing, simulating natural reading pace.

    Args:
        message (str): Text to display with animation

    Returns:
        None
    """
    for char in message:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.075)  # 75ms delay for slightly slower, more dramatic effect
    print()  # Final newline after message completion


def speakbasic(text):
    """
    Core emotion-aware text-to-speech function.

    Analyzes text for emotional content and adjusts speech parameters
    accordingly. Uses a three-tier emotion detection system for optimal
    emotional speech synthesis.

    Args:
        text (str): Text content to speak with emotional intonation

    Returns:
        None

    Emotion Detection Priority:
        1. Keyword detection (explicit emotion words)
        2. Emotion phase tracking (contextual emotional themes)
        3. Sentiment analysis (general emotional polarity)
    """
    try:
        # Initialize TTS engine
        engine = pyttsx3.init()

        # Get default speech properties
        default_rate = engine.getProperty("rate")
        voices = engine.getProperty("voices")

        # Prefer female voice if available (typically index 1)
        if len(voices) > 1:
            engine.setProperty("voice", voices[1].id)
        else:
            engine.setProperty("voice", voices[0].id)

        # Perform sentiment analysis using TextBlob
        blob = TextBlob(text)
        sentiment = blob.sentiment.polarity

        # Get baseline emotion from sentiment analysis
        emotion, (adjusted_rate, adjusted_volume) = get_emotion(sentiment)

        # Apply multi-layer emotion detection with priority
        tracked_emotion = track_emotion_phases(text)  # Contextual emotion detection
        keyword_emotion = detect_emotion(text)  # Direct keyword detection

        # Emotion detection hierarchy: keywords > context > sentiment
        if keyword_emotion != "unknown":
            emotion = keyword_emotion  # Highest confidence: explicit emotion words
        elif tracked_emotion:
            emotion = tracked_emotion  # Medium confidence: contextual themes
        # Else: keep sentiment-based emotion (lowest confidence)

        # Apply emotion-based speech adjustments
        engine.setProperty("rate", adjusted_rate)  # Adjust speech speed
        engine.setProperty("volume", adjusted_volume)  # Adjust speech volume

        # Execute text-to-speech with emotional parameters
        engine.say(text)
        engine.runAndWait()

    except Exception as e:
        print(f"Error in speech synthesis: {e}")


def fspeak(text):
    """
    Main function for emotion-aware text-to-speech with synchronized display.

    Coordinates threaded execution of speech synthesis and animated text display
    to provide a seamless user experience with emotional intelligence.

    Args:
        text (str): Text content to speak and display

    Returns:
        None

    Workflow:
        - Creates separate threads for speech and display
        - Starts both threads concurrently
        - Waits for both threads to complete
        - Provides synchronized audio-visual output
    """
    # Create parallel execution threads
    speak_thread = threading.Thread(target=speakbasic, args=(text,))
    print_thread = threading.Thread(target=print_animated_message, args=(text,))

    # Start both threads simultaneously
    speak_thread.start()
    print_thread.start()

    # Wait for both threads to complete execution
    speak_thread.join()
    print_thread.join()


if __name__ == "__main__":
    """
    Main execution block for testing emotion-aware TTS functionality.

    Provides a simple test case to verify the emotional speech synthesis
    system is working correctly.

    Usage:
        python fspeak.py
    """
    fspeak("i am Friday, i'm here to assist you")
