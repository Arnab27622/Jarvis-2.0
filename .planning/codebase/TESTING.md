# Testing Strategy

## Current State
- **Manual Testing**: Primary method of verification.
- **Root Test Script**: `test.py` used for ad-hoc tests and feature verification.

## Missing Patterns
- **Unit Testing**: No formal `pytest` or `unittest` suite detected.
- **Automated CI**: No GitHub Actions or similar CI configuration found.

## Future Recommendations
- Implement a `tests/` directory.
- Add unit tests for core logic in `assistant/core`.
- Implement integration tests for LLM and API connectors.

---
*Last updated: 2026-04-26 after initial mapping*
