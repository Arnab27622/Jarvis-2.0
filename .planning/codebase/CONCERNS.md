# Technical Concerns

## Technical Debt
- **High Dependency Count**: Over 100 packages in `requirements.txt` increases surface area for conflicts and security vulnerabilities.
- **Lack of Automated Tests**: Reliance on manual testing (`test.py`) makes the codebase fragile to regressions.

## Security
- **API Key Management**: Extensive reliance on external APIs requires careful handling of secrets in `.env`.
- **Environment Exposure**: Ensure `.env` is always ignored and only `.env.example` is shared.

## Performance
- **Heavy ML Dependencies**: `torch` and related libraries lead to large installation size and potentially high resource usage (RAM/CPU).
- **Synchronicity**: Need to ensure all blocking I/O is properly handled with `asyncio`.

---
*Last updated: 2026-04-26 after initial mapping*
