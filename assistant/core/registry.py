"""
A command dispatching system that routes input text to registered handlers
using keyword, regex, and fuzzy matching strategies.
"""

import re
import inspect
from rapidfuzz import process, fuzz

DEBUG_REGISTRY = True

class CommandRegistry:
    """
    Manages command registration and execution across multiple matching tiers.
    """
    def __init__(self):
        self._keyword_handlers = []
        self._regex_handlers = []
        self._fuzzy_handlers = []

    def register_keyword(self, keywords, handler, priority=0):
        """Registers a handler triggered by specific keyword presence."""
        if isinstance(keywords, str):
            keywords = [keywords]
        self._keyword_handlers.append((keywords, handler, priority))
        self._keyword_handlers.sort(key=lambda x: x[2], reverse=True)

    def register_regex(self, pattern, handler, priority=0):
        """Registers a handler triggered by a regex pattern match."""
        self._regex_handlers.append((re.compile(pattern, re.IGNORECASE), handler, priority))
        self._regex_handlers.sort(key=lambda x: x[2], reverse=True)

    def register_fuzzy(self, phrases, handler, score_cutoff=80, priority=0):
        """Registers a handler triggered by fuzzy string similarity."""
        if isinstance(phrases, str):
            phrases = [phrases]
        self._fuzzy_handlers.append((phrases, handler, score_cutoff, priority))
        self._fuzzy_handlers.sort(key=lambda x: x[3], reverse=True)

    def execute(self, text: str) -> bool:
        """
        Attempts to match text against registered handlers in order of priority.
        """
        # Tier 1: Keyword / Exact Match
        for keywords, handler, _ in self._keyword_handlers:
            if any(kw in text for kw in keywords):
                if DEBUG_REGISTRY:
                    print(f"[Registry] Exact Match: '{text}' -> {handler.__name__}")
                return self._run_handler(handler, text)

        # Tier 2: Regex Match (for parameters)
        for pattern, handler, _ in self._regex_handlers:
            match = pattern.search(text)
            if match:
                if DEBUG_REGISTRY:
                    print(f"[Registry] Regex Match: '{pattern.pattern}' -> {handler.__name__}")
                return self._run_handler(handler, text, match)

        # Tier 3: Fuzzy Match (for variations)
        best_overall_match = None
        for phrases, handler, cutoff, _ in self._fuzzy_handlers:
            match = process.extractOne(text, phrases, scorer=fuzz.WRatio)
            if match and match[1] >= cutoff:
                if best_overall_match is None or match[1] > best_overall_match[1]:
                    best_overall_match = (handler, match[1])
        
        if best_overall_match:
            if DEBUG_REGISTRY:
                print(f"[Registry] Fuzzy Match: '{text}' (Score: {best_overall_match[1]:.1f}) -> {best_overall_match[0].__name__}")
            return self._run_handler(best_overall_match[0], text)

        return False

    def _run_handler(self, handler, text, match=None):
        """Invokes a handler with appropriate arguments based on signature."""
        sig = inspect.signature(handler)
        params = sig.parameters
        
        if match and hasattr(match, 'groupdict'):
            kwargs = match.groupdict()
            valid_kwargs = {k: v for k, v in kwargs.items() if k in params}
            if valid_kwargs:
                handler(**valid_kwargs)
                return True
                
        args = []
        if "text" in params:
            args.append(text)
        elif len(params) > 0 and match:
            groups = match.groups()
            if groups:
                args.extend(groups)
            else:
                args.append(match.group(0))
        elif len(params) > 0:
            args.append(text)
            
        handler(*args[:len(params)])
        return True

cmd_registry = CommandRegistry()

def on_keywords(keywords, priority=0):
    """Decorator to register a keyword-based command."""
    def decorator(handler_func):
        cmd_registry.register_keyword(keywords, handler_func, priority)
        return handler_func
    return decorator

def on_regex(pattern, priority=0):
    """Decorator to register a regex-based command."""
    def decorator(handler_func):
        cmd_registry.register_regex(pattern, handler_func, priority)
        return handler_func
    return decorator

def on_fuzzy(phrases, score_cutoff=80, priority=0):
    """Decorator to register a fuzzy-matched command."""
    def decorator(handler_func):
        cmd_registry.register_fuzzy(phrases, handler_func, score_cutoff, priority)
        return handler_func
    return decorator

def on_condition(condition_func, priority=0):
    """Decorator to register a conditional command."""
    def decorator(handler_func):
        cmd_registry.register_keyword([], lambda text: condition_func(text) and handler_func(text), priority)
        return handler_func
    return decorator
