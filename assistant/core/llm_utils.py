"""
LLM Utilities Module - Shared Text Processing and Context Management

Provides centralized utilities for LLM response cleaning, sentence segmentation,
conversation history management, and persistent Q&A storage.
"""

import re
import markdown
from bs4 import BeautifulSoup
import strip_markdown
from typing import List, Dict
from assistant.automation.features.save_data_locally import (
    qa_lock,
    qa_file_path,
    qa_dict,
    save_qa_data,
)
from num2words import num2words as _num2words

def clean_llm_output(raw_text: str) -> str:
    """
    Unified cleaning pipeline for LLM outputs.
    Removes markdown, HTML, and normalizes whitespace/Unicode.
    """
    if not raw_text:
        return ""

    # We no longer strip markdown so the React UI can render code blocks and formatting.
    clean = raw_text

    # 3. Unicode normalization (safe to keep)
    replacements = {
        "â": "'", "ð": "", "â€œ": '"', "â€ ": '"', "â€˜": "'",
        "â€™": "'", "â€¦": "...", "â€¢": "-", "â€”": "--", "â€“": "-"
    }
    for old, new in replacements.items():
        clean = clean.replace(old, new)
    # (g4f promotional ads removed as it is no longer supported)

    # 6. Strip LaTeX commands and symbols that TTS struggles with (without removing markdown chars)
    clean = clean.replace('$', '')
    # Remove rogue trailing asterisks attached to punctuation (e.g., "mind.* ") without breaking math "1 * 2" or "**bold**"
    clean = re.sub(r'([.,!?])\*+(?=\s|$)', r'\1', clean)
    clean = re.sub(r'\\text\{([^}]*)\}', r'\1', clean)
    clean = clean.replace(r'\times', 'times')
    clean = clean.replace(r'\div', 'divided by')
    clean = clean.replace(r'\pm', 'plus or minus')
    clean = clean.replace(r'\approx', 'approximately')
    clean = clean.replace(r'\neq', 'not equal to')
    clean = clean.replace(r'\leq', 'less than or equal to')
    clean = clean.replace(r'\geq', 'greater than or equal to')
    clean = clean.replace(r'\rightarrow', 'implies')
    clean = clean.replace(r'\leftarrow', 'is implied by')
    clean = clean.replace(r'\infty', 'infinity')

    # 7. Normalize whitespace (preserve indentation and single newlines)
    clean = clean.strip()
    clean = re.sub(r"\n{3,}", "\n\n", clean)

    return clean

# ---------------------------------------------------------------------------
# TTS Text Normalization Pipeline
# ---------------------------------------------------------------------------
# Kokoro TTS has no built-in text normalization. This pipeline converts
# units, symbols, abbreviations, ordinals, fractions, and chemical formulas
# into speakable English BEFORE Kokoro ever sees the text.
# ---------------------------------------------------------------------------


# ---- Stage 1 & 3 dictionaries ----
# (unit_regex_suffix, singular, plural)
_UNITS_WITH_NUMBER = [
    # Pressure / weather
    (r'hPa',    'hectopascal',   'hectopascals'),
    (r'kPa',    'kilopascal',    'kilopascals'),
    (r'Pa',     'pascal',        'pascals'),
    (r'atm',    'atmosphere',    'atmospheres'),
    (r'psi',    'P S I',         'P S I'),
    # Temperature (handled specially for ° prefix)
    # Length
    (r'km',     'kilometer',     'kilometers'),
    (r'cm',     'centimeter',    'centimeters'),
    (r'mm',     'millimeter',    'millimeters'),
    (r'nm',     'nanometer',     'nanometers'),
    (r'mi',     'mile',          'miles'),
    (r'ft',     'foot',          'feet'),
    (r'yd',     'yard',          'yards'),
    (r'in',     'inch',          'inches'),
    # Mass
    (r'kg',     'kilogram',      'kilograms'),
    (r'mg',     'milligram',     'milligrams'),
    (r'lb',     'pound',         'pounds'),
    (r'oz',     'ounce',         'ounces'),
    # Time
    (r'ms',     'millisecond',    'milliseconds'),
    (r'ns',     'nanosecond',     'nanoseconds'),
    (r'μs',     'microsecond',    'microseconds'),
    (r'mins',    'minute',        'minutes'),
    (r'min',     'minute',        'minutes'),
    # Data
    (r'TB',     'terabyte',      'terabytes'),
    (r'GB',     'gigabyte',      'gigabytes'),
    (r'MB',     'megabyte',      'megabytes'),
    (r'KB',     'kilobyte',      'kilobytes'),
    (r'Gbps',   'gigabits per second',  'gigabits per second'),
    (r'Mbps',   'megabits per second',  'megabits per second'),
    (r'Kbps',   'kilobits per second',  'kilobits per second'),
    # Frequency
    (r'THz',    'terahertz',     'terahertz'),
    (r'GHz',    'gigahertz',     'gigahertz'),
    (r'MHz',    'megahertz',     'megahertz'),
    (r'kHz',    'kilohertz',     'kilohertz'),
    (r'Hz',     'hertz',         'hertz'),
    # Power / Energy / Electrical
    (r'kWh',    'kilowatt hour', 'kilowatt hours'),
    (r'kW',     'kilowatt',      'kilowatts'),
    (r'MW',     'megawatt',      'megawatts'),
    (r'mAh',    'milliamp hour', 'milliamp hours'),
    (r'mA',     'milliamp',      'milliamps'),
    (r'dB',     'decibel',       'decibels'),
    (r'px',     'pixel',         'pixels'),
    (r'rad',    'radian',        'radians'),
    # These single-letter units need a non-word-char lookahead to be safe
    (r'W(?=[^a-zA-Z]|$)',  'watt',   'watts'),
    (r'V(?=[^a-zA-Z]|$)',  'volt',   'volts'),
    (r'A(?=[^a-zA-Z]|$)',  'amp',    'amps'),
    # Misc
    (r'm(?=[^a-zA-Z/]|$)', 'meter',  'meters'),
    (r'g(?=[^a-zA-Z/]|$)', 'gram',   'grams'),
    (r'L(?=[^a-zA-Z/]|$)', 'liter',  'liters'),
    (r's(?=[^a-zA-Z/]|$)', 'second', 'seconds'),
]

# ---- Stage 2: Compound rate units ----
_COMPOUND_UNITS = [
    (r'm/s²',   'meters per second squared'),
    (r'm/s',    'meters per second'),
    (r'km/h',   'kilometers per hour'),
    (r'km/hr',  'kilometers per hour'),
    (r'mi/h',   'miles per hour'),
    (r'ft/s',   'feet per second'),
    (r'kg/m³',  'kilograms per cubic meter'),
    (r'g/cm³',  'grams per cubic centimeter'),
    (r'W/m²',   'watts per square meter'),
    (r'J/kg',   'joules per kilogram'),
    (r'L/min',  'liters per minute'),
    (r'rpm',    'revolutions per minute'),
]

# ---- Stage 3: Standalone units (no number attached) ----
_STANDALONE_UNITS = {
    'hPa':  'hectopascals',
    'kPa':  'kilopascals',
    'mph':  'miles per hour',
    'kph':  'kilometers per hour',
    'Hz':   'hertz',
    'MHz':  'megahertz',
    'GHz':  'gigahertz',
    'kHz':  'kilohertz',
    'THz':  'terahertz',
    'kW':   'kilowatts',
    'MW':   'megawatts',
    'kWh':  'kilowatt hours',
    'mAh':  'milliamp hours',
    'dB':   'decibels',
    'rpm':  'revolutions per minute',
    'Mbps': 'megabits per second',
    'Gbps': 'gigabits per second',
    'Kbps': 'kilobits per second',
}

# ---- Stage 5: Common abbreviations ----
_COUNTRY_CODES = {
    "AD": "Andorra", "AE": "United Arab Emirates", "AF": "Afghanistan", "AG": "Antigua and Barbuda",
    "AL": "Albania", "AM": "Armenia", "AO": "Angola", "AQ": "Antarctica",
    "AR": "Argentina", "AS": "American Samoa", "AT": "Austria", "AU": "Australia", "AW": "Aruba",
    "AX": "Aland Islands", "AZ": "Azerbaijan", "BA": "Bosnia and Herzegovina", "BB": "Barbados",
    "BD": "Bangladesh", "BE": "Belgium", "BF": "Burkina Faso", "BG": "Bulgaria", "BH": "Bahrain",
    "BI": "Burundi", "BJ": "Benin", "BL": "Saint Barthelemy", "BM": "Bermuda", "BN": "Brunei",
    "BO": "Bolivia", "BQ": "Bonaire", "BR": "Brazil", "BS": "Bahamas", "BT": "Bhutan",
    "BV": "Bouvet Island", "BW": "Botswana", "BY": "Belarus", "BZ": "Belize", "CA": "Canada",
    "CC": "Cocos Islands", "CD": "Democratic Republic of the Congo", "CF": "Central African Republic",
    "CG": "Republic of the Congo", "CH": "Switzerland", "CI": "Ivory Coast", "CK": "Cook Islands",
    "CL": "Chile", "CM": "Cameroon", "CN": "China", "CO": "Colombia", "CR": "Costa Rica",
    "CU": "Cuba", "CV": "Cape Verde", "CW": "Curacao", "CX": "Christmas Island", "CY": "Cyprus",
    "CZ": "Czech Republic", "DE": "Germany", "DJ": "Djibouti", "DK": "Denmark", "DM": "Dominica",
    "DO": "Dominican Republic", "DZ": "Algeria", "EC": "Ecuador", "EE": "Estonia", "EG": "Egypt",
    "EH": "Western Sahara", "ER": "Eritrea", "ES": "Spain", "ET": "Ethiopia", "FI": "Finland",
    "FJ": "Fiji", "FK": "Falkland Islands", "FM": "Micronesia", "FO": "Faroe Islands", "FR": "France",
    "GA": "Gabon", "GB": "United Kingdom", "GD": "Grenada", "GE": "Georgia", "GF": "French Guiana",
    "GG": "Guernsey", "GH": "Ghana", "GI": "Gibraltar", "GL": "Greenland", "GM": "Gambia",
    "GN": "Guinea", "GP": "Guadeloupe", "GQ": "Equatorial Guinea", "GR": "Greece",
    "GS": "South Georgia and the South Sandwich Islands", "GT": "Guatemala", "GU": "Guam",
    "GW": "Guinea-Bissau", "GY": "Guyana", "HK": "Hong Kong", "HM": "Heard Island and McDonald Islands",
    "HN": "Honduras", "HR": "Croatia", "HT": "Haiti", "HU": "Hungary", "ID": "Indonesia",
    "IE": "Ireland", "IL": "Israel", "IM": "Isle of Man", "IN": "India", "IO": "British Indian Ocean Territory",
    "IQ": "Iraq", "IR": "Iran", "IS": "Iceland", "IT": "Italy", "JE": "Jersey", "JM": "Jamaica",
    "JO": "Jordan", "JP": "Japan", "KE": "Kenya", "KG": "Kyrgyzstan", "KH": "Cambodia",
    "KI": "Kiribati", "KM": "Comoros", "KN": "Saint Kitts and Nevis", "KP": "North Korea",
    "KR": "South Korea", "KW": "Kuwait", "KY": "Cayman Islands", "KZ": "Kazakhstan", "LA": "Laos",
    "LB": "Lebanon", "LC": "Saint Lucia", "LI": "Liechtenstein", "LK": "Sri Lanka", "LR": "Liberia",
    "LS": "Lesotho", "LT": "Lithuania", "LU": "Lowembourg", "LV": "Latvia", "LY": "Libya",
    "MA": "Morocco", "MC": "Monaco", "MD": "Moldova", "ME": "Montenegro", "MF": "Saint Martin",
    "MG": "Madagascar", "MH": "Marshall Islands", "MK": "North Macedonia", "ML": "Mali",
    "MM": "Myanmar", "MN": "Mongolia", "MO": "Macao", "MP": "Northern Mariana Islands",
    "MQ": "Martinique", "MR": "Mauritania", "MS": "Montserrat", "MT": "Malta", "MU": "Mauritius",
    "MV": "Maldives", "MW": "Malawi", "MX": "Mexico", "MY": "Malaysia", "MZ": "Mozambique",
    "NA": "Namibia", "NC": "New Caledonia", "NE": "Niger", "NF": "Norfolk Island", "NG": "Nigeria",
    "NI": "Nicaragua", "NL": "Netherlands", "NO": "Norway", "NP": "Nepal", "NR": "Nauru",
    "NU": "Niue", "NZ": "New Zealand", "OM": "Oman", "PA": "Panama", "PE": "Peru", "PF": "French Polynesia",
    "PG": "Papua New Guinea", "PH": "Philippines", "PK": "Pakistan", "PL": "Poland", "PM": "Saint Pierre and Miquelon",
    "PN": "Pitcairn", "PR": "Puerto Rico", "PS": "Palestine", "PT": "Portugal", "PW": "Palau",
    "PY": "Paraguay", "QA": "Qatar", "RE": "Reunion", "RO": "Romania", "RS": "Serbia", "RU": "Russia",
    "RW": "Rwanda", "SA": "Saudi Arabia", "SB": "Solomon Islands", "SC": "Seychelles", "SD": "Sudan",
    "SE": "Sweden", "SG": "Singapore", "SH": "Saint Helena", "SI": "Slovenia", "SJ": "Svalbard and Jan Mayen",
    "SK": "Slovakia", "SL": "Sierra Leone", "SM": "San Marino", "SN": "Senegal", "SO": "Somalia",
    "SR": "Suriname", "SS": "South Sudan", "ST": "Sao Tome and Principe", "SV": "El Salvador",
    "SX": "Sint Maarten", "SY": "Syria", "SZ": "Swaziland", "TC": "Turks and Caicos Islands",
    "TD": "Chad", "TF": "French Southern Territories", "TG": "Togo", "TH": "Thailand",
    "TJ": "Tajikistan", "TK": "Tokelau", "TL": "East Timor", "TM": "Turkmenistan", "TN": "Tunisia",
    "TO": "Tonga", "TR": "Turkey", "TT": "Trinidad and Tobago", "TV": "Tuvalu", "TW": "Taiwan",
    "TZ": "Tanzania", "UA": "Ukraine", "UG": "Uganda", "UM": "United States Minor Outlying Islands",
    "US": "United States", "UY": "Uruguay", "UZ": "Uzbekistan", "VA": "Vatican", "VC": "Saint Vincent and the Grenadines",
    "VE": "Venezuela", "VG": "British Virgin Islands", "VI": "U.S. Virgin Islands", "VN": "Vietnam",
    "VU": "Vanuatu", "WF": "Wallis and Futuna", "WS": "Samoa", "YE": "Yemen", "YT": "Mayotte",
    "ZA": "South Africa", "ZM": "Zambia", "ZW": "Zimbabwe"
}

_CASE_SENSITIVE_ABBREVIATIONS = []
for code, name in _COUNTRY_CODES.items():
    _CASE_SENSITIVE_ABBREVIATIONS.append((rf'\b{code}\b', name))

_CASE_INSENSITIVE_ABBREVIATIONS = [
    # Must come before shorter patterns to avoid partial matches
    (r'\bVS Code\b',     'V S Code'),
    (r'\bUSD\b',         'U S D'),
    (r'\bAPI\b',         'A P I'),
    (r'\bUI\b',          'U I'),
    (r'\bAI\b',          'A I'),
    (r'\bw/o\b',         'without'),
    (r'\bb/w\b',         'between'),
    (r'\bw/(?=\s|$)',     'with'),
    (r'\bMr\.',          'Mister'),
    (r'\bMrs\.',         'Missus'),
    (r'\bMs\.',          'Miss'),
    (r'\bDr\.',          'Doctor'),
    (r'\bProf\.',        'Professor'),
    (r'\bJr\.',          'Junior'),
    (r'\bSr\.',          'Senior'),
    (r'\bSt\.',          'Saint'),
    (r'\betc\.',         'etcetera'),
    (r'\be\.g\.',        'for example'),
    (r'\bi\.e\.',        'that is'),
    (r'\bapprox\.',      'approximately'),
    (r'\bgovt\.',        'government'),
    (r'\bdept\.',        'department'),
    (r'\binc\.',         'incorporated'),
    (r'\bcorp\.',        'corporation'),
    (r'\bltd\.',         'limited'),
    (r'\bno\.\s*(?=\d)', 'number '),
    (r'\bvs\.\b',        'versus'),
    (r'\bvs\b',          'versus'),
    (r'\byrs\b',         'years'),
    (r'\byr\b',          'year'),
    (r'\bhrs\b',         'hours'),
    (r'\bhr\b',          'hour'),
    (r'\bapprox\b',      'approximately'),
    # Standalone time abbreviation mappings
    (r'\bmins\b',        'minutes'),
    (r'\bmin\b',         'minute'),
    (r'\bsecs\b',        'seconds'),
    (r'\bsec\b',         'second'),
    # Phonetic spelling corrections
    (r'\bmiliseconds\b',  'milliseconds'),
    (r'\bmilisecond\b',   'millisecond'),
]

# ---- Stage 8: Known chemical formulas ----
_CHEMICAL_FORMULAS = {
    'CO₂': 'C O 2',   'CO2': 'C O 2',
    'H₂O': 'H 2 O',   'H2O': 'H 2 O',
    'O₂':  'O 2',      'O2':  'O 2',
    'N₂':  'N 2',      'N2':  'N 2',
    'H₂':  'H 2',      'H2':  'H 2',
    'CH₄': 'C H 4',    'CH4': 'C H 4',
    'NH₃': 'N H 3',    'NH3': 'N H 3',
    'SO₂': 'S O 2',    'SO2': 'S O 2',
    'NO₂': 'N O 2',    'NO2': 'N O 2',
    'Fe₂O₃': 'F E 2 O 3', 'Fe2O3': 'F E 2 O 3',
    'NaCl': 'N A C L',
    'CaCO₃': 'C A C O 3', 'CaCO3': 'C A C O 3',
}

# ---- Stage 9: Unicode subscript / superscript digit mapping ----
_SUBSCRIPT_MAP = str.maketrans('₀₁₂₃₄₅₆₇₈₉', '0123456789')
_SUPERSCRIPT_MAP = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹', '0123456789')

# ---- Common fractions for Stage 7 ----
_COMMON_FRACTIONS = {
    (1, 2): 'one half',
    (1, 3): 'one third',
    (2, 3): 'two thirds',
    (1, 4): 'one quarter',
    (3, 4): 'three quarters',
    (1, 5): 'one fifth',
    (2, 5): 'two fifths',
    (3, 5): 'three fifths',
    (4, 5): 'four fifths',
    (1, 6): 'one sixth',
    (5, 6): 'five sixths',
    (1, 8): 'one eighth',
    (3, 8): 'three eighths',
    (5, 8): 'five eighths',
    (7, 8): 'seven eighths',
    (1, 10): 'one tenth',
}


def normalize_for_tts(text: str) -> str:
    """
    Semantic text normalization pipeline for Kokoro TTS.

    Converts units, symbols, abbreviations, ordinals, fractions, and chemical
    formulas into speakable English. Runs 9 ordered stages; order matters
    because later stages depend on earlier ones.
    """
    if not text or not text.strip():
        return text

    # ── Stage 1: Temperature units (special — has ° prefix) ──
    text = re.sub(r'(-?\d+\.?\d*)\s*°C\b', lambda m: f'{_minus(m.group(1))} degrees Celsius', text)
    text = re.sub(r'(-?\d+\.?\d*)\s*°F\b', lambda m: f'{_minus(m.group(1))} degrees Fahrenheit', text)
    text = re.sub(r'(-?\d+\.?\d*)\s*°K\b', lambda m: f'{_minus(m.group(1))} Kelvin', text)

    # ── Stage 1: Number + unit compounds ──
    for unit_pat, singular, plural in _UNITS_WITH_NUMBER:
        pattern = rf'(-?\d+\.?\d*)\s*{unit_pat}(?![a-zA-Z])'
        text = re.sub(pattern, lambda m, s=singular, p=plural: f'{_minus(m.group(1))} {_pluralize(m.group(1), s, p)}', text)

    # ── Stage 2: Compound rate units ──
    for unit_str, expansion in _COMPOUND_UNITS:
        # Escape special regex chars in the unit string, then use word boundaries
        escaped = re.escape(unit_str)
        text = re.sub(rf'\b{escaped}\b', expansion, text)

    # ── Stage 3: Standalone unit symbols ──
    for unit_str, expansion in _STANDALONE_UNITS.items():
        escaped = re.escape(unit_str)
        text = re.sub(rf'\b{escaped}\b', expansion, text)

    # ── Stage 4: Symbol-to-word expansion ──
    # Currency
    text = re.sub(r'\$(\d+(?:,\d+)*(?:\.\d+)?)', r'\1 dollars', text)
    text = re.sub(r'€(\d+(?:,\d+)*(?:\.\d+)?)', r'\1 euros', text)
    text = re.sub(r'£(\d+(?:,\d+)*(?:\.\d+)?)', r'\1 pounds', text)
    # Math / comparison symbols (order matters: multi-char before single-char)
    text = text.replace('±', ' plus or minus ')
    text = text.replace('≈', ' approximately ')
    text = text.replace('≠', ' not equal to ')
    text = text.replace('≤', ' less than or equal to ')
    text = text.replace('≥', ' greater than or equal to ')
    text = text.replace('→', ' leads to ')
    text = text.replace('←', ' from ')
    text = text.replace('×', ' times ')
    text = text.replace('÷', ' divided by ')
    text = text.replace('²', ' squared')
    text = text.replace('³', ' cubed')
    # Decimal numbers (10.54 → 10 point 54)
    text = re.sub(r'(?<=\d)\.(?=\d)', ' point ', text)
    # Degree symbol (orphaned, not part of °C/°F — those are already handled)
    text = re.sub(r'(\d)\s*°', r'\1 degrees', text)
    # Common single-char symbols
    text = text.replace('%', ' percent')
    text = text.replace('&', ' and ')
    text = re.sub(r'(?<=\w)@(?=\w)', ' at ', text)     # word@word → word at word
    text = re.sub(r'(?<=[\w+])\+(?=[\w+]|$)', ' plus ', text)   # C++ → C plus plus, 3+5 → 3 plus 5
    text = text.replace('=', ' equals ')
    text = re.sub(r'(?<!\<)\<(?!\<)', ' less than ', text)   # < but not <<
    text = re.sub(r'(?<!\>)\>(?!\>)', ' greater than ', text) # > but not >>
    text = text.replace('~', ' approximately ')

    # Time AM/PM
    text = re.sub(r'(?<=\d)\s*a\.?m\.?(?=\s|$|\W)', ' A M', text, flags=re.IGNORECASE)
    text = re.sub(r'(?<=\d)\s*p\.?m\.?(?=\s|$|\W)', ' P M', text, flags=re.IGNORECASE)

    # ── Stage 5: Common abbreviations (MUST run before slash→'or' to handle w/o, w/, b/w) ──
    for pattern, replacement in _CASE_SENSITIVE_ABBREVIATIONS:
        text = re.sub(pattern, replacement, text)
        
    for pattern, replacement in _CASE_INSENSITIVE_ABBREVIATIONS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Slash between words (but NOT number/number which is handled by Stage 7)
    text = re.sub(r'(?<=[a-zA-Z])/(?=[a-zA-Z])', ' or ', text)

    # ── Stage 6: Ordinal numbers (1st, 2nd, 3rd, 21st, etc.) ──
    def _expand_ordinal(m):
        try:
            num = int(m.group(1))
            return _num2words(num, to='ordinal')
        except Exception:
            return m.group(0)

    text = re.sub(r'\b(\d+)(?:st|nd|rd|th)\b', _expand_ordinal, text, flags=re.IGNORECASE)

    # ── Stage 7: Fractions and ratios ──
    def _expand_fraction(m):
        num, den = int(m.group(1)), int(m.group(2))
        # Skip date-like patterns (checked by context after the match)
        if den > 100:
            return m.group(0)  # likely a date like 1/4/2025
        if (num, den) in _COMMON_FRACTIONS:
            return _COMMON_FRACTIONS[(num, den)]
        return f'{num} over {den}'

    # Only match number/number NOT followed by /number (which would be a date)
    text = re.sub(r'\b(\d{1,3})/(\d{1,3})\b(?!/)', _expand_fraction, text)

    # ── Stage 8: Chemical formulas ──
    for formula, expansion in _CHEMICAL_FORMULAS.items():
        text = re.sub(rf'\b{re.escape(formula)}\b', expansion, text)

    # ── Stage 9: Final cleanup ──
    # Convert remaining subscript/superscript digits to regular digits
    text = text.translate(_SUBSCRIPT_MAP)
    text = text.translate(_SUPERSCRIPT_MAP)
    # Collapse multiple spaces
    text = re.sub(r'[ \t]{2,}', ' ', text)

    return text.strip()


def _minus(num_str: str) -> str:
    """Convert a negative number string to 'minus X' for natural speech."""
    if num_str.startswith('-'):
        return f'minus {num_str[1:]}'
    return num_str


def _pluralize(num_str: str, singular: str, plural: str) -> str:
    """Return singular or plural form based on the numeric value."""
    try:
        val = float(num_str.lstrip('-'))
        if val == 1.0:
            return singular
        return plural
    except ValueError:
        return plural


def clean_for_speech(raw_text: str) -> str:
    """
    Aggressive cleaning strictly for Text-To-Speech (TTS).
    Removes all Markdown, HTML, backticks, asterisks, etc.
    Skips over code blocks so they are not spoken aloud.
    Then runs normalize_for_tts() to convert units/symbols into speakable words.
    """
    if not raw_text:
        return ""
        
    # Remove markdown code blocks completely before parsing (supports both closed and unclosed code blocks)
    clean = re.sub(r'```.*?(?:```|$)', ' ', raw_text, flags=re.DOTALL)
        
    # 1. Convert Markdown to HTML then strip tags
    html = markdown.markdown(clean)
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ")

    # 2. Strip remaining markdown syntax
    try:
        clean = strip_markdown.strip_markdown(text)
    except Exception:
        clean = text

    # 3. Strip code characters
    clean = clean.replace('\\', ' ')
    clean = clean.replace('*', '')
    clean = clean.replace('`', '')
    clean = re.sub(r'_{2,}', ' blank ', clean)
    clean = clean.replace('_', ' ')
    clean = clean.replace('#', '')

    # 4. Semantic text normalization (MUST run before non-printable strip
    #    so it can see Unicode symbols like °, ², ³, ₂, etc.)
    clean = normalize_for_tts(clean)

    # 5. Remove non-printable characters (safe now — all Unicode symbols are expanded)
    clean = re.sub(r"[^\x20-\x7E\u00A0-\u00FF\u2013\u2014\u2018\u2019\u201C\u201D]", "", clean)

    # 6. Normalize whitespace
    clean = clean.strip()
    clean = re.sub(r"\n+", " ", clean)
    clean = re.sub(r"[ \t]{2,}", " ", clean)

    return clean

def split_sentences(text: str) -> List[str]:
    """Splits text into chunks, preserving ALL whitespace and newlines for the UI.
       Ensures that markdown code blocks (```...```) are kept entirely intact as single chunks.
    """
    parts = re.split(r'(?<=[.!?])(\s+)', text)
    
    sentences = []
    current_sentence = ""
    
    for part in parts:
        current_sentence += part
        # Check if we are inside a code block by counting backticks
        in_code_block = current_sentence.count("```") % 2 != 0
        
        # Only split if we are NOT inside a code block, and we hit a whitespace separator
        if not in_code_block and re.match(r'^\s+$', part):
            if len(current_sentence.strip()) > 2:
                sentences.append(current_sentence)
                current_sentence = ""
                
    if current_sentence.strip():
        sentences.append(current_sentence)
        
    return sentences

def trim_history(history: List[Dict[str, str]], max_messages: int = 10) -> List[Dict[str, str]]:
    """Manages conversation context size while preserving the system prompt."""
    if not history:
        return []
    
    sys_msg = history[0] if history[0].get("role") == "system" else None
    content_msgs = history[1:] if sys_msg else history
    
    if len(content_msgs) > max_messages:
        content_msgs = content_msgs[-max_messages:]
        
    return ([sys_msg] if sys_msg else []) + content_msgs

def should_cache_offline(query: str, response: str) -> bool:
    """Determines if a Q&A pair is factual and should be permanently cached."""
    query = query.lower().strip()
    
    # Exclude creative/conversational keywords
    creative_kws = ["story", "joke", "poem", "funny", "random", "tell me", "write", "create", "generate", "how to", "code"]
    if any(kw in query for kw in creative_kws):
        return False
        
    # Include factual/definitional keywords
    factual_kws = ["what is", "what are", "who is", "who are", "where is", "define", "explain"]
    if any(query.startswith(kw) or kw in query for kw in factual_kws):
        return True
        
    return False

def save_to_brain(query: str, answer: str) -> None:
    """Stores successful Q&A pair in the local intelligence database if it is factual."""
    if not should_cache_offline(query, answer):
        return
        
    with qa_lock:
        qa_dict[query] = answer
        save_qa_data(qa_file_path, qa_dict)
