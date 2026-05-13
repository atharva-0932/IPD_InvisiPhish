"""
Dataset utilities for InvisiPhish training.

Downloads and prepares the two corpora specified in the paper (Section IV-A):
  1. SMS Spam Collection (UCI) — 5,574 SMS messages
  2. Nazario Phishing Corpus (GitHub, 2021-2023 subset) + SpamAssassin ham

Usage:
    from training.dataset_utils import build_combined_dataset
    df = build_combined_dataset()   # columns: label (0/1), message, source
"""

import os
import re
import email
import zipfile
import tarfile
import subprocess
from datetime import datetime
from typing import List
from email.utils import parsedate_to_datetime

import requests
import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(DATA_DIR, exist_ok=True)

SMS_SPAM_URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/00228/smsspamcollection.zip"
SPAMASSASSIN_HAM_URLS = [
    "https://spamassassin.apache.org/old/publiccorpus/20030228_easy_ham.tar.bz2",
    "https://spamassassin.apache.org/old/publiccorpus/20030228_easy_ham_2.tar.bz2",
    "https://spamassassin.apache.org/old/publiccorpus/20030228_hard_ham.tar.bz2",
]
SPAMASSASSIN_SPAM_URLS = [
    "https://spamassassin.apache.org/old/publiccorpus/20030228_spam.tar.bz2",
    "https://spamassassin.apache.org/old/publiccorpus/20030228_spam_2.tar.bz2",
]
# Kept for reference — repo was removed from GitHub as of 2025
NAZARIO_REPO = "https://github.com/jnazario/phishing-corpus.git"

# Phishing keywords used to detect non-boilerplate sections
_PHISHING_KWS = {"verify", "account", "password", "login", "bank", "urgent", "click", "update", "secure"}


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------

def _download(url: str, dest: str) -> str:
    """Download url → dest unless already cached."""
    if os.path.exists(dest):
        print(f"  [cache] {os.path.basename(dest)}")
        return dest
    print(f"  [download] {url}")
    r = requests.get(url, timeout=120, stream=True)
    r.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in r.iter_content(chunk_size=65536):
            f.write(chunk)
    return dest


# ---------------------------------------------------------------------------
# SMS Spam Collection
# ---------------------------------------------------------------------------

def load_sms_spam_collection() -> pd.DataFrame:
    """Returns DataFrame[label: 'spam'|'ham', message: str]."""
    zip_path = os.path.join(DATA_DIR, "smsspamcollection.zip")
    _download(SMS_SPAM_URL, zip_path)

    with zipfile.ZipFile(zip_path) as z:
        with z.open("SMSSpamCollection") as f:
            lines = f.read().decode("utf-8", errors="ignore").strip().splitlines()

    rows = []
    for line in lines:
        parts = line.split("\t", 1)
        if len(parts) == 2:
            label, msg = parts
            rows.append({"label": label.strip(), "message": msg.strip()})

    df = pd.DataFrame(rows)
    counts = df["label"].value_counts().to_dict()
    print(f"  [sms_spam] {len(df)} messages — {counts}")
    return df


# ---------------------------------------------------------------------------
# Email parsing helpers
# ---------------------------------------------------------------------------

def _parse_date(msg: email.message.Message) -> datetime | None:
    date_str = msg.get("Date", "")
    if not date_str:
        return None
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        return None


def _extract_text(msg: email.message.Message) -> str:
    parts = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    parts.append(part.get_payload(decode=True).decode("utf-8", errors="ignore"))
                except Exception:
                    pass
    else:
        try:
            parts.append(msg.get_payload(decode=True).decode("utf-8", errors="ignore"))
        except Exception:
            pass
    return " ".join(parts).strip()


def _strip_boilerplate_footer(text: str, min_tokens: int = 50) -> str:
    """
    Remove trailing boilerplate footers (>50 tokens, no phishing keywords).
    Paper spec Section IV-A: 'Boilerplate footers (>50 tokens, no phishing keywords) removed.'
    """
    lines = text.splitlines()
    cutoff = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        chunk = " ".join(lines[i:])
        tokens = chunk.split()
        if len(tokens) > min_tokens:
            if not any(kw in chunk.lower() for kw in _PHISHING_KWS):
                cutoff = i
    return "\n".join(lines[:cutoff]).strip()


# ---------------------------------------------------------------------------
# Nazario Phishing Corpus
# ---------------------------------------------------------------------------

def load_nazario_phishing_corpus(start_year: int = 2021, end_year: int = 2023) -> List[str]:
    """
    Attempts to clone jnazario/phishing-corpus and extract emails timestamped
    between start_year and end_year.

    Paper spec: 1,206 phishing emails (Jan 2021 – Dec 2023 subset).

    Fallback: if the GitHub repo is unavailable (it was removed in 2025),
    returns SpamAssassin spam corpus instead and logs a warning.
    """
    nazario_dir = os.path.join(DATA_DIR, "nazario")

    if not os.path.exists(nazario_dir):
        print(f"  [clone] Cloning jnazario/phishing-corpus (shallow)…")
        try:
            subprocess.run(
                ["git", "clone", "--depth=1", NAZARIO_REPO, nazario_dir],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as exc:
            print(
                f"  [warn] Nazario corpus clone failed ({exc.returncode}). "
                "The jnazario/phishing-corpus GitHub repo was removed. "
                "Falling back to SpamAssassin spam corpus as phishing email source."
            )
            # Remove the incomplete clone dir if created
            import shutil
            if os.path.exists(nazario_dir):
                shutil.rmtree(nazario_dir)
            return load_spamassassin_spam()
    else:
        print(f"  [cache] Nazario corpus already cloned.")

    texts = []
    for root, _dirs, files in os.walk(nazario_dir):
        for fname in files:
            if fname.startswith("."):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "rb") as f:
                    raw = f.read()
                msg = email.message_from_bytes(raw)
                dt = _parse_date(msg)
                if dt is None or not (start_year <= dt.year <= end_year):
                    continue
                subject = msg.get("Subject", "")
                body = _extract_text(msg)
                body = _strip_boilerplate_footer(body)
                text = f"{subject} {body}".strip()
                if text:
                    texts.append(text)
            except Exception:
                continue

    if not texts:
        print(f"  [warn] No emails found in Nazario corpus for {start_year}–{end_year}. Falling back to SpamAssassin spam.")
        return load_spamassassin_spam()

    print(f"  [nazario] {len(texts)} phishing emails ({start_year}–{end_year})")
    return texts


# ---------------------------------------------------------------------------
# SpamAssassin Ham Corpus
# ---------------------------------------------------------------------------

def _load_spamassassin_tarballs(urls: List[str]) -> List[str]:
    """Helper: download and parse a list of SpamAssassin tarball URLs."""
    texts = []
    for url in urls:
        fname = url.split("/")[-1]
        dest = os.path.join(DATA_DIR, fname)
        _download(url, dest)
        try:
            with tarfile.open(dest, "r:bz2") as tar:
                for member in tar.getmembers():
                    if not member.isfile():
                        continue
                    fobj = tar.extractfile(member)
                    if fobj is None:
                        continue
                    try:
                        raw = fobj.read()
                        msg = email.message_from_bytes(raw)
                        body = _extract_text(msg)
                        body = _strip_boilerplate_footer(body)
                        if body:
                            texts.append(body)
                    except Exception:
                        continue
        except Exception as exc:
            print(f"  [warn] Could not parse {fname}: {exc}")
    return texts


def load_spamassassin_ham() -> List[str]:
    """
    Downloads SpamAssassin public ham corpora and returns list of email texts.
    Used as the legitimate email counterpart to the phishing email corpus.
    """
    texts = _load_spamassassin_tarballs(SPAMASSASSIN_HAM_URLS)
    print(f"  [spamassassin_ham] {len(texts)} legitimate emails loaded")
    return texts


def load_spamassassin_spam() -> List[str]:
    """
    Downloads SpamAssassin public spam corpora (~1,896 spam emails).
    Used as a fallback phishing email source when Nazario corpus is unavailable.
    """
    texts = _load_spamassassin_tarballs(SPAMASSASSIN_SPAM_URLS)
    print(f"  [spamassassin_spam] {len(texts)} spam/phishing emails loaded (fallback)")
    return texts


# ---------------------------------------------------------------------------
# Deduplication (paper spec: Jaccard > 0.85 removed pre-split)
# ---------------------------------------------------------------------------

def _jaccard(a: set, b: set) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 1.0


def deduplicate(texts: List[str], threshold: float = 0.85) -> List[str]:
    """
    Remove near-duplicate messages where Jaccard similarity > threshold
    on word-token sets. O(n²) — acceptable for n < 15,000.
    """
    token_sets = [set(t.lower().split()) for t in texts]
    kept_texts, kept_sets = [], []
    for text, ts in zip(texts, token_sets):
        if not any(_jaccard(ts, ks) > threshold for ks in kept_sets):
            kept_texts.append(text)
            kept_sets.append(ts)
    removed = len(texts) - len(kept_texts)
    if removed:
        print(f"  [dedup] Removed {removed} near-duplicates (J>{threshold})")
    return kept_texts


# ---------------------------------------------------------------------------
# Combined dataset builder
# ---------------------------------------------------------------------------

def build_combined_dataset() -> pd.DataFrame:
    """
    Builds the full training corpus per paper Section IV-A.

    Returns DataFrame with columns:
        label   int   1=phishing, 0=legitimate
        message str   raw text
        source  str   origin corpus

    Split is NOT applied here — callers handle 70/10/20 split.
    """
    print("\n=== Building combined dataset ===")
    rows = []

    # 1. SMS Spam Collection
    sms_df = load_sms_spam_collection()
    for _, row in sms_df.iterrows():
        rows.append({
            "label": 1 if row["label"] == "spam" else 0,
            "message": row["message"],
            "source": "sms_spam",
        })

    # 2. Nazario phishing emails (2021-2023 subset)
    nazario = load_nazario_phishing_corpus(2021, 2023)

    # 3. SpamAssassin ham — sample to match Nazario count (stratified by length)
    ham_all = load_spamassassin_ham()
    ham_sorted = sorted(ham_all, key=len)
    n = len(nazario)
    if len(ham_sorted) >= n:
        step = len(ham_sorted) / n
        ham_sampled = [ham_sorted[int(i * step)] for i in range(n)]
    else:
        ham_sampled = ham_sorted

    for text in nazario:
        rows.append({"label": 1, "message": text, "source": "nazario"})
    for text in ham_sampled:
        rows.append({"label": 0, "message": text, "source": "spamassassin_ham"})

    df = pd.DataFrame(rows)

    # Per-class deduplication before split
    phishing_texts = deduplicate(df[df["label"] == 1]["message"].tolist())
    legit_texts    = deduplicate(df[df["label"] == 0]["message"].tolist())

    final_rows = (
        [{"label": 1, "message": m, "source": "phishing"} for m in phishing_texts] +
        [{"label": 0, "message": m, "source": "legitimate"} for m in legit_texts]
    )
    df_final = pd.DataFrame(final_rows).sample(frac=1, random_state=42).reset_index(drop=True)

    phishing_count = int(df_final["label"].sum())
    legit_count    = len(df_final) - phishing_count
    print(f"\n  [dataset] Total: {len(df_final)} | Phishing: {phishing_count} | Legit: {legit_count}")
    return df_final
