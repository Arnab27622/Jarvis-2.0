# Phase 01: The YouTube Fix - Plan

## 1. Goal
Fix the YouTube query truncation bug and optimize command implementation using fuzzy matching and regex-based extraction.

## 2. Technical Approach
- **Library**: Install `rapidfuzz` for high-performance fuzzy matching.
- **Normalization**: Centralize command cleaning (lower, punctuation, filler words).
- **Regex**: Use `re.search` patterns to accurately capture parameters.
- **Registry**: Extend `CommandRegistry` to prioritize matching tiers.

## 3. Tasks

### Wave 1: Infrastructure & Normalization
- [ ] **Task 1: Dependencies**
  - `<read_first>`: `requirements.txt`
  - `<action>`: Run `pip install rapidfuzz` and add it to `requirements.txt`.
  - `<acceptance_criteria>`: `pip list` contains `rapidfuzz`.

- [ ] **Task 2: Normalization Function**
  - `<read_first>`: `assistant/interface/commands.py`
  - `<action>`: Implement `normalize_command(text)` in `commands.py` to strip "jarvis", filler words, and punctuation.
  - `<acceptance_criteria>`: `commands.py` contains `def normalize_command`.

### Wave 2: Registry Refactor
- [ ] **Task 3: Upgrade CommandRegistry**
  - `<read_first>`: `assistant/interface/commands.py`
  - `<action>`: Update `CommandRegistry` and decorators to support `@on_regex` and `@on_fuzzy`.
  - `<acceptance_criteria>`: `CommandRegistry.execute` uses normalization and tiered matching.

### Wave 3: Command Implementation
- [ ] **Task 4: Fix YouTube & Web Search**
  - `<read_first>`: `assistant/interface/commands.py`
  - `<action>`: Replace `split()` logic in `handle_youtube_play`, `handle_youtube_search`, and `handle_web_search` with Regex patterns.
  - `<acceptance_criteria>`: `handle_youtube_play` uses `re.search`.

- [ ] **Task 5: Optimize Variations**
  - `<read_first>`: `assistant/interface/commands.py`
  - `<action>`: Apply `@on_fuzzy` to volume, alarm, and reminder commands to handle semantic variations.
  - `<acceptance_criteria>`: Volume commands trigger with "make it louder".

## 4. Verification Plan

### Automated/Scripted
- Create a test script `verify_commands.py` that calls `normalize_command` and `cmd_registry.execute` with various inputs.

### Manual UAT
- [ ] "play python tutorials on youtube" -> "Playing python tutorials on YouTube"
- [ ] "hey jarvis, could you please turn the volume up" -> Volume increases.
- [ ] "search for spaceX in wikipedia" -> Wikipedia search triggered.
- [ ] "set an alarm for 7 am" -> Alarm set.
