import sys
import threading
import time
import pyttsx3
from textblob import TextBlob


def detect_emotion(text: str) -> str:
    text_lower = text.lower()

    # keywords for different feelings
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

    # Check for each emotion
    for emotion, keywords in emotion_keywords.items():
        if any(word in text_lower for word in keywords):
            return emotion

    return "unknown"


def get_emotion(sentiment):
    # TextBlob sentiment is between -1 and 1
    if sentiment > 0.7:
        return "ecstatic", (220, 1.5)
    elif sentiment > 0.6:
        return "overjoyed", (180, 1.4)
    elif sentiment > 0.5:
        return "elated", (190, 1.3)
    elif sentiment > 0.4:
        return "joyful", (180, 1.2)
    elif sentiment > 0.3:
        return "happy", (170, 1.1)
    elif sentiment > 0.2:
        return "cheerful", (160, 1.0)
    elif sentiment > 0.1:
        return "content", (150, 0.9)
    elif sentiment > 0.05:
        return "pleased", (140, 0.8)
    elif sentiment > -0.05:
        return "neutral", (130, 1)
    elif sentiment > -0.1:
        return "indifferent", (120, 1)
    elif sentiment > -0.2:
        return "unhappy", (110, 1)
    elif sentiment > -0.3:
        return "sad", (100, 1)
    elif sentiment > -0.4:
        return "mournful", (100, 1)
    elif sentiment > -0.5:
        return "despondent", (170, 1)
    elif sentiment > -0.6:
        return "melancholy", (170, 0.1)
    elif sentiment > -0.7:
        return "depressed", (60, 1)
    elif sentiment > -0.8:
        return "devastated", (180, 1)
    elif sentiment > -0.9:
        return "hopeful", (175, 1.3)
    else:
        return "distressed", (100, 0.8)


def track_emotion_phases(text):
    text_lower = text.lower()

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

    for emotion, words in emotion_categories.items():
        if any(word in text_lower for word in words):
            return emotion

    return None


def print_animated_message(message):
    for char in message:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.075)
    print()


def speakbasic(text):
    try:
        engine = pyttsx3.init()

        # Get default rate and voices
        default_rate = engine.getProperty("rate")
        voices = engine.getProperty("voices")

        # Set default voice (female if available)
        if len(voices) > 1:
            engine.setProperty("voice", voices[1].id)
        else:
            engine.setProperty("voice", voices[0].id)

        # Analyze sentiment
        blob = TextBlob(text)
        sentiment = blob.sentiment.polarity

        # Get emotion from sentiment
        emotion, (adjusted_rate, adjusted_volume) = get_emotion(sentiment)

        # Check for emotion keywords that might override sentiment analysis
        tracked_emotion = track_emotion_phases(text)
        keyword_emotion = detect_emotion(text)

        # Priority: keyword detection > tracked emotion > sentiment analysis
        if keyword_emotion != "unknown":
            emotion = keyword_emotion
        elif tracked_emotion:
            emotion = tracked_emotion

        # Adjust speech based on emotion
        engine.setProperty("rate", adjusted_rate)
        engine.setProperty("volume", adjusted_volume)

        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"Error in speech synthesis: {e}")


def fspeak(text):
    # Create threads
    speak_thread = threading.Thread(target=speakbasic, args=(text,))
    print_thread = threading.Thread(target=print_animated_message, args=(text,))

    # Start threads
    speak_thread.start()
    print_thread.start()

    # Wait for both threads to complete
    speak_thread.join()
    print_thread.join()


if __name__ == "__main__":
    fspeak("i am Friday, i'm here to assist you")
