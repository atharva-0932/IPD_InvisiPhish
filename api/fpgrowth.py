"""
FP-Growth inference module for InvisiPhish.

Paper spec (Section III-C-1):
  - At inference, compute token-set overlap between input and the mined
    frequent-itemset library to produce mFP ∈ [0, 1].
  - mFP = (# itemsets that are subsets of the input token set) / (total itemsets)
  - Serialized itemsets are loaded from api/models/fp_itemsets.pkl (generated
    by running:  python -m training.fpgrowth_trainer)

Fallback:
  - If the pkl file is not yet present (model not trained), falls back to the
    legacy weighted-keyword scorer so the API remains functional.
"""

import os
import re
import pickle
import logging

import nltk
import spacy
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import CountVectorizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# NLP resource setup (same as before — needed for extract_keywords)
# ---------------------------------------------------------------------------

def _nltk_download_ssl_safe(resources: list):
    """Download NLTK resources with SSL verification disabled (macOS cert fix)."""
    import ssl
    orig = getattr(ssl, "_create_default_https_context", None)
    ssl._create_default_https_context = ssl._create_unverified_context
    for res, path in resources:
        try:
            nltk.data.find(path)
        except LookupError:
            nltk.download(res, quiet=True)
    if orig is not None:
        ssl._create_default_https_context = orig

_nltk_download_ssl_safe([
    ("stopwords", "corpora/stopwords"),
    ("wordnet",   "corpora/wordnet"),
])

try:
    _nlp = spacy.load("en_core_web_sm")
except OSError:
    _nlp = None
    logger.warning("spaCy model 'en_core_web_sm' not found. Run: python -m spacy download en_core_web_sm")

_lemmatizer = WordNetLemmatizer()
_stop_words = set(stopwords.words("english"))

# ---------------------------------------------------------------------------
# Load mined FP-Growth itemsets
# ---------------------------------------------------------------------------

_ITEMSETS_PATH = os.path.join(os.path.dirname(__file__), "models", "fp_itemsets.pkl")
_fp_artifact: dict | None = None


def _load_artifact() -> dict:
    """Lazy-load the serialized FP-Growth artifact."""
    global _fp_artifact
    if _fp_artifact is None:
        if os.path.exists(_ITEMSETS_PATH):
            with open(_ITEMSETS_PATH, "rb") as f:
                _fp_artifact = pickle.load(f)
            n = len(_fp_artifact.get("itemsets", []))
            logger.info(f"[fpgrowth] Loaded {n} frequent itemsets from {_ITEMSETS_PATH}")
        else:
            logger.warning(
                "[fpgrowth] fp_itemsets.pkl not found — using legacy keyword scorer. "
                "Run: python -m training.fpgrowth_trainer"
            )
            _fp_artifact = {}
    return _fp_artifact


def _itemsets() -> list:
    return _load_artifact().get("itemsets", [])


# ---------------------------------------------------------------------------
# Token-set computation (shared by trainer and inference)
# ---------------------------------------------------------------------------

def _tokenize_to_set(text: str) -> set:
    """Normalize text → set of unique lemmatized tokens (no stopwords, len > 2)."""
    text = re.sub(r'https?://\S+|www\.\S+', ' ', text.lower())
    text = re.sub(r'[^a-z\s]', ' ', text)
    return {
        _lemmatizer.lemmatize(w)
        for w in text.split()
        if w not in _stop_words and len(w) > 2
    }


# ---------------------------------------------------------------------------
# Core scoring — paper equation: mFP = matched / total
# ---------------------------------------------------------------------------

def compute_fp_score(token_set: set) -> float:
    """
    Compute mFP ∈ [0, 1]: fraction of known phishing itemsets that are
    subsets of the input token set.

    Returns 0.0 when no itemsets are loaded (not yet trained).
    """
    itemset_list = _itemsets()
    if not itemset_list:
        return 0.0
    matches = sum(1 for itemset in itemset_list if itemset.issubset(token_set))
    return round(matches / len(itemset_list), 6)


# ---------------------------------------------------------------------------
# Legacy keyword scorer (fallback when model not yet trained)
# ---------------------------------------------------------------------------

HIGH_RISK_KEYWORDS = {
    "password", "login", "verify", "account", "fraud", "bank", "security", "breach",
    "credential", "authentication", "personal", "identity", "compromise", "unauthorized",
    "transaction", "verification", "restricted", "confidential", "malware", "spyware",
    "ransomware", "otp", "debit", "credit", "billing", "statement", "scam", "hijack",
    "phishing", "data theft", "stolen", "blacklisted", "unusual activity", "privacy alert",
    "wire transfer", "unauthorized payment", "identity theft", "emergency", "recovery",
    "breached", "security alert", "banking", "secure", "verified", "account locked",
    "suspicious login", "sensitive", "login failure", "security breach", "reset password",
    "data leak", "cyber attack", "fraudulent", "fraud alert", "suspicious transaction",
    "financial alert", "immediate action", "credit freeze", "cvv", "pin", "2fa", "mfa",
}
MEDIUM_RISK_KEYWORDS = {
    "alert", "access", "confirm", "update", "reset", "warning", "suspicious", "refund",
    "urgent", "notify", "dispute", "locked", "reactivate", "payment", "unpaid", "overdue",
    "penalty", "subscription", "renewal", "invoice", "pending", "troubleshoot",
    "customer support", "maintenance", "verify now", "password change", "restricted access",
    "technical support", "system update", "login attempt", "recovery code", "notification",
    "verification required", "service disruption", "pending update", "pending payment",
    "information update", "suspicious behavior", "account notice", "system maintenance",
}
LOW_RISK_KEYWORDS = {
    "click", "free", "offer", "limited", "prize", "winner", "claim", "congratulations",
    "lucky", "lottery", "jackpot", "bonus", "exclusive", "trial", "cash", "cheap",
    "investment", "discount", "deal", "coupon", "gift", "reward", "promo", "unlimited",
    "guarantee", "special", "savings", "act now", "hurry", "instant cash",
}


def _legacy_keyword_score(keywords: list) -> float:
    """Weighted keyword score (legacy fallback). Returns score in [0, 100]."""
    score = 0
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in HIGH_RISK_KEYWORDS:
            score += 20
        elif kw_lower in MEDIUM_RISK_KEYWORDS:
            score += 15
        elif kw_lower in LOW_RISK_KEYWORDS:
            score += 10
    return float(min(100, score))


# ---------------------------------------------------------------------------
# Keyword extraction (kept for API response display)
# ---------------------------------------------------------------------------

def extract_keywords(text: str) -> list:
    """
    Extracts notable tokens via NER + CountVectorizer frequency.
    Used for the 'extracted_keywords' display field in the API response.
    """
    if not text or not text.strip():
        return []

    cleaned = re.sub(r'[^a-z\s]', '', text.lower())
    words = [
        _lemmatizer.lemmatize(w)
        for w in cleaned.split()
        if w not in _stop_words and len(w) > 2
    ]
    if len(words) < 2:
        return []

    ner_keywords = set()
    if _nlp is not None:
        doc = _nlp(" ".join(words))
        ner_keywords = {ent.text.lower() for ent in doc.ents}

    try:
        vec = CountVectorizer(max_features=10, stop_words="english")
        vec.fit_transform([" ".join(words)])
        freq_keywords = set(vec.get_feature_names_out())
    except ValueError:
        freq_keywords = set()

    final = ner_keywords | freq_keywords
    return list(final) if len(final) > 1 else []


# ---------------------------------------------------------------------------
# Public API — same signature as before
# ---------------------------------------------------------------------------

def process_message(
    message_type: str,
    original_text: str | None = None,
    email_subject: str | None = None,
    email_body: str | None = None,
) -> dict:
    """
    Analyze a message and return FP-Growth phishing score.

    Returns dict with keys:
        extracted_keywords  list[str]   display keywords
        final_score         float       0–100 (mFP * 100, or legacy score)
        final_result        str         'high risk phishing' | 'medium risk phishing' | 'legit'
        mfp_raw             float       raw mFP ∈ [0, 1] (0 if using legacy fallback)
        itemsets_matched    int         how many itemsets fired
        using_trained_model bool        True = real FP-Growth, False = legacy fallback
    """
    if message_type not in ("sms", "email"):
        raise ValueError("message_type must be 'sms' or 'email'")

    text = (
        original_text if message_type == "sms"
        else f"{email_subject or ''} {email_body or ''}".strip()
    )

    extracted_keywords = extract_keywords(text)
    token_set = _tokenize_to_set(text)
    itemset_list = _itemsets()
    using_trained = bool(itemset_list)

    if using_trained:
        mfp_raw = compute_fp_score(token_set)
        score = round(mfp_raw * 100, 2)
        matched = int(mfp_raw * len(itemset_list))
    else:
        # Legacy fallback
        mfp_raw = 0.0
        score = _legacy_keyword_score(extracted_keywords)
        matched = 0

    if score >= 80:
        final_result = "high risk phishing"
    elif score >= 30:
        final_result = "medium risk phishing"
    else:
        final_result = "legit"

    return {
        "extracted_keywords":  extracted_keywords,
        "final_score":         score,
        "final_result":        final_result,
        "mfp_raw":             mfp_raw,
        "itemsets_matched":    matched,
        "using_trained_model": using_trained,
    }
