"""Skill extraction from free text.

Deliberately rule-based (taxonomy + word-boundary regex) rather than a trained
NER model. It is fast, deterministic, explainable and needs no model download —
and it is the right baseline to beat before you reach for spaCy or an LLM.

Upgrade path is noted at the bottom of the file.
"""

from __future__ import annotations

import re
from functools import lru_cache

from app.data.skills import (
    ALIAS_TO_CANONICAL,
    SKILL_TAXONOMY,
    SKIP_BARE_ALIASES,
    canonicalise_all,
)


@lru_cache(maxsize=1)
def _compiled_patterns() -> list[tuple[re.Pattern[str], str]]:
    """Compile one regex per alias, longest first so 'Node.js' beats 'Node'.

    Two details that matter in practice:

    * `\\b` breaks next to '+' and '#', so 'c' would match inside 'C++'.
      Lookarounds that also reject '+' and '#' fix that.
    * Aliases of one or two characters ('ml', 'js', 'c') are only matched in
      upper case, which is how they appear when they really are a skill.
    """
    patterns: list[tuple[re.Pattern[str], str]] = []
    aliases = sorted(ALIAS_TO_CANONICAL.items(), key=lambda kv: len(kv[0]), reverse=True)

    for alias, canonical in aliases:
        alias = alias.strip()
        if alias in SKIP_BARE_ALIASES:
            continue

        escaped = re.escape(alias)
        pattern = rf"(?<![A-Za-z0-9+#]){escaped}(?![A-Za-z0-9+#])"

        if len(alias) <= 2:
            # Case-sensitive, upper case only: 'ML' yes, 'ml' in 'html' no.
            escaped_upper = re.escape(alias.upper())
            pattern = rf"(?<![A-Za-z0-9+#]){escaped_upper}(?![A-Za-z0-9+#])"
            patterns.append((re.compile(pattern), canonical))
        else:
            patterns.append((re.compile(pattern, re.IGNORECASE), canonical))

    return patterns


def extract_skills(text: str, sections: dict[str, str] | None = None) -> list[str]:
    """Return canonical skills found in the text.

    Skills named in an explicit SKILLS section are ranked first, since those
    are the ones the candidate is actually claiming.
    """
    if not text:
        return []

    found: dict[str, int] = {}
    for pattern, canonical in _compiled_patterns():
        hits = len(pattern.findall(text))
        if hits:
            found[canonical] = found.get(canonical, 0) + hits

    if not found:
        return []

    skills_section = (sections or {}).get("skills", "")
    priority: set[str] = set()
    if skills_section:
        for pattern, canonical in _compiled_patterns():
            if pattern.search(skills_section):
                priority.add(canonical)

    # Sort: declared-in-skills-section first, then by frequency, then A-Z.
    ordered = sorted(
        found.items(),
        key=lambda kv: (kv[0] not in priority, -kv[1], kv[0].lower()),
    )
    return [name for name, _ in ordered]


def extract_skills_with_counts(text: str) -> dict[str, int]:
    """Same matching, but returns how often each skill appeared."""
    counts: dict[str, int] = {}
    for pattern, canonical in _compiled_patterns():
        hits = len(pattern.findall(text or ""))
        if hits:
            counts[canonical] = counts.get(canonical, 0) + hits
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


def normalise_job_skills(skills: list[str]) -> list[str]:
    """Canonicalise skills that came in through the API."""
    return canonicalise_all(skills)


def taxonomy_size() -> int:
    return len(SKILL_TAXONOMY)


# ----------------------------------------------------------------------
# Upgrade path, in order of effort:
#
# 1. spaCy PhraseMatcher over the same taxonomy — handles inflection and
#    tokenisation better than regex, still deterministic.
# 2. A trained NER model (spaCy `ner` component) on labelled resumes, to catch
#    skills that are not in the taxonomy at all.
# 3. An LLM extraction pass with a strict JSON schema, used only for the
#    leftovers the rule-based pass missed. Keep the rules: they are free,
#    instant, and they make the LLM output auditable.
# ----------------------------------------------------------------------
