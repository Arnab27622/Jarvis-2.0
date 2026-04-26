# Requirements - Command Optimization

## 1. Functional Requirements

### 1.1 Bug Fixes
- **FR-1.1.1 (YouTube Query Integrity)**: The system must extract the search query accurately without truncating words that contain common prepositions (e.g., "python" should not be cut at "on").
- **FR-1.1.2 (Parameter Extraction)**: All commands that take dynamic input (reminders, alarms, search queries) must use robust parsing that doesn't rely on simple string indexing.

### 1.2 Command Robustness (Optimization)
- **FR-1.2.1 (Phrase Variation)**: Existing commands must respond to semantic variations of their activation phrases.
  - *Example*: "increase volume", "volume up", "make it louder" should all trigger the same handler.
- **FR-1.2.2 (Case & Whitespace Insensitivity)**: All matching must be normalized to handle irregular speech-to-text output.

### 1.3 Implementation Quality
- **FR-1.3.1 (Registry Refactor)**: The `CommandRegistry` should be updated to allow for easier extension of matching logic (e.g., adding regex or fuzzy match capabilities).
- **FR-1.3.2 (Maintainability)**: Consolidate redundant keyword lists and simplify handler logic.

## 2. Non-Functional Requirements
- **NFR-2.1 (Performance)**: Command matching must happen in < 50ms to maintain assistant responsiveness.
- **NFR-2.2 (Stability)**: New matching logic must not introduce false positives for existing commands.

## 3. Verification Criteria (UAT)
- **UAT-1 (The Python Test)**: User says "play python tutorials on youtube". Assistant should respond with "Playing python tutorials on YouTube" (not "pyth").
- **UAT-2 (Semantic Test)**: User says "hey jarvis, could you please turn the volume down a bit". Assistant should trigger the volume decrease handler.
- **UAT-3 (Regression Test)**: All existing commands (time, date, joke, etc.) still work with their original keywords.
