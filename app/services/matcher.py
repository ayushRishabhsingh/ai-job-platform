"""The recommendation engine.

Three strategies, in increasing order of sophistication, all behind one
interface so the API surface never changes:

    v1  overlap    matched_required_skills / required_skills
    v2  tfidf      cosine similarity of TF-IDF vectors (resume vs job text)
    v3  embedding  cosine similarity of sentence-transformer embeddings

`overlap` is the default because it is instant, needs no model, and is fully
explainable — you can always show the user *which* skills matched. The other two
blend a semantic score with the overlap score so the explanation survives.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from app.data.skills import canonicalise_all


class MatchStrategy(str, Enum):
    OVERLAP = "overlap"
    TFIDF = "tfidf"
    EMBEDDING = "embedding"


@dataclass
class MatchResult:
    score: float  # 0-100
    matched_skills: list[str]
    missing_skills: list[str]
    strategy: str

    @property
    def coverage(self) -> str:
        required = len(self.matched_skills) + len(self.missing_skills)
        return f"{len(self.matched_skills)}/{required} skills"


# ----------------------------------------------------------------------
# v1 — skill overlap
# ----------------------------------------------------------------------
def skill_overlap(user_skills: list[str], job_skills: list[str]) -> MatchResult:
    """score = matched required skills / total required skills."""
    user_set = {s.lower(): s for s in canonicalise_all(user_skills)}
    required = canonicalise_all(job_skills)

    matched = [s for s in required if s.lower() in user_set]
    missing = [s for s in required if s.lower() not in user_set]

    score = (len(matched) / len(required) * 100) if required else 0.0
    return MatchResult(
        score=round(score, 1),
        matched_skills=matched,
        missing_skills=missing,
        strategy=MatchStrategy.OVERLAP.value,
    )


def weighted_overlap(
    user_skills: list[str],
    job_skills: list[str],
    user_experience: int = 0,
    job_experience: int = 0,
) -> MatchResult:
    """Overlap, adjusted for the experience gap.

    Being under-experienced costs more than being over-experienced, which
    matches how screening actually works.
    """
    base = skill_overlap(user_skills, job_skills)
    gap = job_experience - user_experience

    if gap > 0:  # noqa: SIM108 - the branches document the asymmetry
        penalty = min(gap * 5.0, 25.0)  # up to -25 for being under-qualified
    else:
        penalty = min(abs(gap) * 1.0, 5.0)  # small -ve for being over-qualified

    base.score = round(max(0.0, min(100.0, base.score - penalty)), 1)
    return base


# ----------------------------------------------------------------------
# v2 — TF-IDF cosine similarity
# ----------------------------------------------------------------------
class TfidfMatcher:
    """Fits a TF-IDF vocabulary over the job corpus, then scores one resume.

    Fit once per request batch, not per job — that is the whole point of
    keeping this in a class.
    """

    def __init__(self, job_texts: list[str]):
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "The tfidf strategy requires scikit-learn: pip install scikit-learn"
            ) from exc

        self._available = bool(job_texts) and any(t.strip() for t in job_texts)
        if not self._available:
            return

        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
            sublinear_tf=True,
        )
        self.job_matrix = self.vectorizer.fit_transform(job_texts)

    def scores_for(self, resume_text: str) -> list[float]:
        """Cosine similarity between the resume and every job, as 0-100."""
        if not self._available or not resume_text.strip():
            return [0.0] * (self.job_matrix.shape[0] if self._available else 0)

        from sklearn.metrics.pairwise import cosine_similarity

        resume_vec = self.vectorizer.transform([resume_text])
        sims = cosine_similarity(resume_vec, self.job_matrix)[0]
        # TF-IDF cosine on short documents rarely exceeds ~0.5, so rescale to
        # keep the numbers meaningful to a human reader.
        return [float(min(100.0, s * 100 * 1.8)) for s in sims]


# ----------------------------------------------------------------------
# v3 — sentence-transformer embeddings
# ----------------------------------------------------------------------
_embedding_model = None


def load_embedding_model(model_name: str):
    """Lazily load and cache the sentence-transformer model."""
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "The embedding strategy requires sentence-transformers: "
            "pip install sentence-transformers"
        ) from exc
    _embedding_model = SentenceTransformer(model_name)
    return _embedding_model


def embedding_available() -> bool:
    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        return False
    return True


def embedding_scores(resume_text: str, job_texts: list[str], model_name: str) -> list[float]:
    """Cosine similarity of embeddings, as 0-100."""
    if not resume_text.strip() or not job_texts:
        return [0.0] * len(job_texts)

    model = load_embedding_model(model_name)
    vectors = model.encode([resume_text] + job_texts, normalize_embeddings=True)
    resume_vec, job_vecs = vectors[0], vectors[1:]
    return [float(max(0.0, min(100.0, float(sum(resume_vec * jv)) * 100))) for jv in job_vecs]


# ----------------------------------------------------------------------
# Blending
# ----------------------------------------------------------------------
def blend(
    semantic_score: float, overlap_result: MatchResult, strategy: str, semantic_weight: float = 0.4
) -> MatchResult:
    """Combine a semantic score with the explainable overlap score.

    Skill overlap keeps most of the weight: a semantic model will happily call a
    frontend resume a 60% match for a backend job because both say "developer".
    """
    combined = overlap_result.score * (1 - semantic_weight) + semantic_score * semantic_weight
    return MatchResult(
        score=round(max(0.0, min(100.0, combined)), 1),
        matched_skills=overlap_result.matched_skills,
        missing_skills=overlap_result.missing_skills,
        strategy=strategy,
    )


def confidence_label(score: float) -> str:
    """Turn a number into something a UI can show as a badge."""
    if score >= 80:
        return "Strong match"
    if score >= 60:
        return "Good match"
    if score >= 40:
        return "Partial match"
    if score > 0:
        return "Weak match"
    return "No match"


def gap_advice(missing_skills: list[str], score: float) -> list[str]:
    """Concrete, non-generic next steps for closing a skill gap."""
    advice: list[str] = []
    if not missing_skills:
        advice.append("You meet every listed requirement — apply now.")
        return advice

    top = missing_skills[: min(3, len(missing_skills))]
    advice.append(f"Highest-leverage gaps to close first: {', '.join(top)}.")

    if score >= 70:
        advice.append(
            "You are already above the usual screening bar. Mention the missing "
            "skills as 'familiar with' rather than skipping the application."
        )
    elif score >= 40:
        advice.append(
            f"Build one small project that uses {top[0]} end to end, then add it "
            "to your resume with a measurable outcome."
        )
    else:
        advice.append(
            "This role is a stretch. Look for postings that overlap more with "
            "your current stack, and treat these skills as a longer-term plan."
        )

    if len(missing_skills) > 3:
        advice.append(
            f"{len(missing_skills) - 3} further skills are listed; they are usually "
            "nice-to-have rather than blocking."
        )
    return advice


def normalised_sigmoid(x: float, midpoint: float = 50.0, steepness: float = 0.08) -> float:
    """Optional score sharpening — pushes mid scores away from the middle."""
    return 100 / (1 + math.exp(-steepness * (x - midpoint)))
