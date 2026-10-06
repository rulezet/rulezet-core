"""Bad inputs for layer 4 (robustness) — shared by every feature.

Each feature picks what applies to its fields; the expectation is always the
same: a clean 4xx (or the value stored safely, escaped), never a 500 and never
a half-written row.
"""

TOO_LONG = "A" * 100_000
EMPTY = ""
BLANK = "   \t\n  "

INJECTIONS = [
    "<script>alert(1)</script>",
    '"><img src=x onerror=alert(1)>',
    "' OR 1=1 --",
    "'; DROP TABLE rule; --",
    "{{7*7}}",
    "{% print 7*7 %}",
    "${7*7}",
    "../../../../etc/passwd",
]

ODD_CHARACTERS = [
    "null\x00byte",
    "control\x01\x02\x1bchars",
    "emoji 🔥🛡️💀",
    "right-to-left ‮gnirts",
    "zero​width",
    "日本語のテキスト",
]

WRONG_TYPES = [None, 12345, 1.5, True, [], {}, ["a", "b"], {"nested": {"x": 1}}]

BAD_IDS = [0, -1, 2**31, 2**63, "abc", "1; DROP TABLE rule", "../1"]
