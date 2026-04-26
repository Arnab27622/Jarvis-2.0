# Phase 01: The YouTube Fix - Context

**Gathered**: 2026-04-26
**Status**: Ready for planning
**Source**: Discuss Phase

<domain>
## Phase Boundary
This phase focuses on refactoring the command processing logic in `assistant/interface/commands.py` to fix parameter extraction bugs (like the YouTube query issue) and optimize the robustness of intent matching for all existing commands.
</domain>

<decisions>
## Implementation Decisions

### Intent Matching Strategy
- **Fuzzy/Semantic Matcher**: Implement a lightweight fuzzy matching system to handle phrase variations (e.g., "louder" vs "increase volume").
- **Latency Constraint**: The matcher must be fast enough to avoid noticeable delays in assistant response (<50ms).
- **Fallback Logic**: Maintain the current hierarchy: Specific Keywords -> Regex -> Fuzzy -> LLM Brain.

### Parameter Extraction
- **Regex-based**: Replace all string splitting logic (`split()`) with robust Regex patterns for extracting:
  - YouTube search queries.
  - Alarm/Reminder times and messages.
  - Web search queries.
  - Image generation prompts.

### Input Normalization
- **Pre-processing Layer**: Implement a normalization function that runs before matching.
- **Filler Word Stripping**: Remove words like "please", "could you", "can you", "hey", and the wake word "jarvis" from the command string.
- **Punctuation**: Strip punctuation to ensure "set alarm?" matches "set alarm".

### Command Registry Architecture
- **Refactor**: Upgrade `CommandRegistry` to handle the new matching types (Keyword, Regex, Fuzzy) and integrated normalization.
- **Clean Code**: Maintain the decorator-based registration pattern if possible, but extend it to support these more complex matching rules.

</decisions>

<canonical_refs>
## Canonical References
- `assistant/interface/commands.py` — Primary target for refactor.
- `assistant/automation/integrations/youtube_automation.py` — Downstream integration for YouTube play.
</canonical_refs>

<specifics>
## Specific Ideas
- The "python/on" bug: "play python tutorials on youtube" should be parsed as query="python tutorials".
- The query extraction regex should likely look for `play (.*) on youtube` or similar patterns.
</specifics>

<deferred>
## Deferred Ideas
- Complex LLM-based semantic routing (saved for future if fuzzy/regex isn't enough).
- Adding new commands.
</deferred>

---
*Phase: 01-the-youtube-fix*
*Context gathered: 2026-04-26*
