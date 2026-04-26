# Roadmap - Command Optimization

## Milestone 1: Stability & Bug Fixes
*Focus: Resolve known issues and prepare for refactor.*

### Phase 1: The YouTube Fix
- Fix the query extraction logic in `assistant/interface/commands.py`.
- Implement unit tests (if possible) or manual verification scripts for common query strings.
- **Depends on**: None

## Milestone 2: Infrastructure Refactor
*Focus: Upgrade the command matching engine.*

### Phase 2: Enhanced Registry
- Refactor `CommandRegistry` to support Regex-based matching.
- Update decorators to allow for optional regex patterns.
- Implement normalization layer (case, whitespace, punctuation).
- **Depends on**: Phase 1

## Milestone 3: Intent Robustness
*Focus: Expand command variations and optimize implementation.*

### Phase 3: Semantic Optimization
- Audit all existing handlers and replace brittle string checks with robust patterns.
- Consolidate similar commands into shared handlers where applicable.
- Final verification against UAT criteria.
- **Depends on**: Phase 2

---
*Last updated: 2026-04-26*
