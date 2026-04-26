# Phase 01: The YouTube Fix - Research

## 1. Fuzzy Matching Library Comparison

| Feature | thefuzz (formerly fuzzywuzzy) | rapidfuzz (Recommended) |
|---------|-------------------------------|--------------------------|
| **Language** | Python (pure) | C++ (with Python bindings) |
| **Performance** | Slow (ms range) | **Extremely Fast (<1ms)** |
| **Dependencies** | python-Levenshtein (optional but needed for speed) | None (Standalone) |
| **Algorithm** | Levenshtein / Token Sort | Levenshtein / Jaro-Winkler / etc. |

**Decision**: Use `rapidfuzz`. It provides the best performance for real-time voice processing without adding heavy dependencies.

## 2. Optimal Regex Patterns for Parameter Extraction

Existing `split()` logic is prone to errors when queries contain prepositions (e.g., "play python tutorials on youtube").

### Proposed Regex Patterns:
- **YouTube Play**: `^play\s+(.*?)(?:\s+on\s+youtube|\s+youtube)?$`
  - *Matches*: "play python tutorials on youtube" -> Group 1: "python tutorials"
  - *Matches*: "play music youtube" -> Group 1: "music"
- **Alarms**: `^(?:set\s+)?(?:an\s+)?alarm\s+(?:for|at|in|after)?\s*(.*)$`
- **Reminders**: `^(?:set\s+)?(?:a\s+)?reminder\s+(?:for|at|to|in|after)?\s*(.*)$`
- **Web Search**: `^(?:search\s+the\s+web\s+for|search\s+web\s+for|search\s+for)\s+(.*)$`

## 3. Input Normalization Logic

To make the assistant feel more natural, we will implement a `normalize_command` function.

### Filler Word List:
`["please", "can you", "could you", "would you mind", "hey", "jarvis", "tell me", "i want to", "start", "run"]`

### Punctuation Handling:
Strip common punctuation: `.,?!;:`

### Normalization Flow:
1. Lowercase text.
2. Strip punctuation.
3. Remove wake word ("jarvis").
4. Remove filler words from the beginning/end of the string.
5. Trim whitespace.

## 4. Registry Refactor Design

The `CommandRegistry` will be updated to support a tiered matching system.

```python
class CommandRegistry:
    def execute(self, text):
        norm_text = normalize(text)
        
        # Tier 1: Exact / Keyword Match
        for handler in self.keyword_handlers:
            if match: return handler()
            
        # Tier 2: Regex Match (for parameters)
        for handler, pattern in self.regex_handlers:
            match = re.match(pattern, norm_text)
            if match: return handler(match.groups())
            
        # Tier 3: Fuzzy Match (for variations)
        best_match = process.extractOne(norm_text, self.fuzzy_phrases)
        if best_match.score > threshold:
            return best_match.handler()
```

---
*Phase: 01-the-youtube-fix*
*Date: 2026-04-26*
