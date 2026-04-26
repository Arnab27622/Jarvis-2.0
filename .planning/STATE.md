# Project State - Command Optimization

## Current Milestone: Milestone 1: Stability & Bug Fixes
## Current Phase: Phase 1: The YouTube Fix

## Active Tasks
- [ ] Initialize project documents. (Completed)
- [ ] Fix YouTube query truncation bug. (Next)

## Blockers
- None

## Recent Learnings
- The `CommandRegistry` currently uses simple `any(kw in text)` which makes it very sensitive to keyword order and overlapping substrings.
- Python's `split()` is being used for parameter extraction, which is the root cause of the "python" -> "pyth" bug due to splitting on "on".

---
*Last updated: 2026-04-26*
