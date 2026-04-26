# Jarvis 2.0 - Command Optimization

## What This Is
A focused effort to refine, fix, and optimize the voice command processing system in Jarvis 2.0, specifically targeting `assistant/interface/commands.py`.

## Core Value
To transform the current command processing from a brittle, keyword-based system into a robust and reliable interaction layer that handles natural language variations seamlessly.

## Context
- **Project Type**: Brownfield (existing Python assistant)
- **Primary Target**: `assistant/interface/commands.py`
- **Key Challenge**: Handling natural language variations and fixing string parsing bugs (e.g., the "python" -> "pyth" truncation).

## Requirements

### Validated
- ✓ Core voice assistant architecture exists.
- ✓ Command registry system is implemented.
- ✓ External APIs (Weather, YouTube, etc.) are functional.

### Active
- [ ] Fix YouTube query truncation bug (the "python/on" issue).
- [ ] Refactor `CommandRegistry` to support more robust matching (Regex/Fuzzy).
- [ ] Improve intent matching for all existing commands to handle phrasing variations.
- [ ] Maintain 100% backward compatibility with existing command functionality.

### Out of Scope
- Adding new commands or features.
- Changing the underlying LLM/Brain logic (unless requested for intent matching).
- Modifying UI/UX components.

## Key Decisions
| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Regex-based Extraction | More reliable than simple `split()` for parameter extraction. | Pending |
| Intent-based Matching | Handles "turn up volume" vs "increase volume" without manual keyword lists. | Pending |

## Evolution
This document evolves at phase transitions.
- **Phase 1 (Fixes)**: Resolve the YouTube bug.
- **Phase 2 (Refactor)**: Upgrade the Registry.
- **Phase 3 (Optimization)**: Broaden intent support.

---
*Last updated: 2026-04-26 after initialization*
