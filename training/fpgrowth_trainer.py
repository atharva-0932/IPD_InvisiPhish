"""
FP-Growth Trainer for InvisiPhish.

Paper spec (Section III-C-1):
  - Messages represented as token-set transactions (bag of unique lemmas)
  - FP-Growth run on phishing-labeled messages only with min_support σ=0.05
  - Inference: token-set overlap with frequent itemset library → mFP ∈ [0, 1]
  - Serializes results to api/models/fp_itemsets.pkl

Usage:
    cd /path/to/IPD_InvisiPhish
    python -m training.fpgrowth_trainer
    python -m training.fpgrowth_trainer --min_support 0.03   # try lower support
"""

import os
import re
import sys
import pickle
import argparse

import nltk
import pandas as pd
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import fpgrowth

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from training.dataset_utils import build_combined_dataset  # noqa: E402

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "api", "models")
OUTPUT_PATH = os.path.join(MODELS_DIR, "fp_itemsets.pkl")
DEFAULT_MIN_SUPPORT = 0.05


# ---------------------------------------------------------------------------
# NLTK resource setup
# ---------------------------------------------------------------------------

def _setup_nltk():
    """
    Download required NLTK corpora.
    On macOS the system SSL certs are often missing from the Python.org
    installer; we patch the default HTTPS context to avoid that failure.
    The permanent fix is: open /Applications/Python 3.14/Install Certificates.command
    """
    import ssl
    try:
        _orig_ctx = ssl._create_default_https_context
    except AttributeError:
        _orig_ctx = None

    # Temporarily disable SSL verification so nltk.download() can reach nltk.org
    ssl._create_default_https_context = ssl._create_unverified_context

    for resource, path in [
        ("stopwords", "corpora/stopwords"),
        ("wordnet",   "corpora/wordnet"),
        ("omw-1.4",   "corpora/omw-1.4"),
    ]:
        try:
            nltk.data.find(path)
        except LookupError:
            nltk.download(resource, quiet=True)

    # Restore original context
    if _orig_ctx is not None:
        ssl._create_default_https_context = _orig_ctx


# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------

def tokenize_to_set(text: str, lemmatizer: WordNetLemmatizer, stop_words: set) -> list:
    """
    Normalize text → list of unique lemmatized tokens.
    Strips URLs, lowercases, removes non-alpha, filters stopwords and short tokens.
    Returns a list (not set) so TransactionEncoder can process it.
    """
    text = re.sub(r'https?://\S+|www\.\S+', ' ', text.lower())
    text = re.sub(r'[^a-z\s]', ' ', text)
    tokens = {
        lemmatizer.lemmatize(w)
        for w in text.split()
        if w not in stop_words and len(w) > 2
    }
    return list(tokens)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train(min_support: float = DEFAULT_MIN_SUPPORT) -> list:
    """
    Mine frequent itemsets from phishing-labeled messages.

    Returns list of frozensets (the mined phishing pattern signatures).
    Saves artifact to api/models/fp_itemsets.pkl.
    """
    _setup_nltk()
    lemmatizer = WordNetLemmatizer()
    stop_words = set(stopwords.words("english"))

    print(f"\n{'='*50}")
    print(f" FP-Growth Trainer  |  σ = {min_support}")
    print(f"{'='*50}")

    df = build_combined_dataset()

    # Only phishing messages feed the FP-Growth miner (paper spec)
    phishing_msgs = df[df["label"] == 1]["message"].tolist()
    print(f"\n[fpgrowth] Building transactions from {len(phishing_msgs)} phishing messages…")

    transactions = [
        tokenize_to_set(msg, lemmatizer, stop_words)
        for msg in phishing_msgs
    ]
    # Drop transactions with fewer than 2 items (FP-Growth needs at least 2)
    transactions = [t for t in transactions if len(t) >= 2]
    print(f"[fpgrowth] {len(transactions)} valid transactions after filtering")

    # --- Apriori pruning: remove infrequent singletons before building the matrix ---
    # Any frequent itemset can only contain frequent items, so this is lossless.
    # Without this, a 13k-token vocabulary makes mlxtend run for hours.
    from collections import Counter
    min_count = int(min_support * len(transactions))
    token_counts = Counter(t for trans in transactions for t in trans)
    frequent_vocab = {tok for tok, cnt in token_counts.items() if cnt >= min_count}
    orig_vocab = sum(len(t) for t in transactions)
    transactions = [[t for t in trans if t in frequent_vocab] for trans in transactions]
    transactions = [t for t in transactions if len(t) >= 2]
    print(f"[fpgrowth] Vocabulary after pruning: {len(frequent_vocab)} frequent tokens "
          f"(pruned {token_counts.__len__() - len(frequent_vocab):,} infrequent tokens, "
          f"min_count={min_count})")
    print(f"[fpgrowth] {len(transactions)} transactions remain after singleton pruning")

    # Encode as binary transaction matrix
    te = TransactionEncoder()
    te_array = te.fit(transactions).transform(transactions)
    df_te = pd.DataFrame(te_array, columns=te.columns_)
    print(f"[fpgrowth] Binary matrix: {df_te.shape[0]} rows × {df_te.shape[1]} cols")

    # Run FP-Growth — cap at itemset length 3 to keep search space tractable
    print(f"[fpgrowth] Mining with min_support={min_support}, max_len=3…")
    frequent_itemsets = fpgrowth(df_te, min_support=min_support, use_colnames=True, max_len=3)

    if frequent_itemsets.empty:
        print("[fpgrowth] WARNING: No itemsets found. Try lowering --min_support.")
        return []

    frequent_itemsets["size"] = frequent_itemsets["itemsets"].apply(len)
    size_dist = frequent_itemsets["size"].value_counts().sort_index().to_dict()
    print(f"[fpgrowth] Found {len(frequent_itemsets)} frequent itemsets")
    print(f"[fpgrowth] Size distribution: {size_dist}")

    # Show top-10 most frequent single-token itemsets for interpretability
    singletons = frequent_itemsets[frequent_itemsets["size"] == 1].nlargest(10, "support")
    if not singletons.empty:
        print("\n[fpgrowth] Top-10 most frequent phishing tokens:")
        for _, row in singletons.iterrows():
            token = list(row["itemsets"])[0]
            print(f"  {token:<25}  support={row['support']:.3f}")

    # Serialize
    itemsets_list = [frozenset(row) for row in frequent_itemsets["itemsets"]]
    os.makedirs(MODELS_DIR, exist_ok=True)

    artifact = {
        "itemsets":      itemsets_list,
        "min_support":   min_support,
        "n_transactions": len(transactions),
        "vocab_size":    df_te.shape[1],
        "size_dist":     size_dist,
    }
    with open(OUTPUT_PATH, "wb") as f:
        pickle.dump(artifact, f)

    print(f"\n[fpgrowth] Saved {len(itemsets_list)} itemsets → {OUTPUT_PATH}")
    print("[fpgrowth] Training complete.\n")
    return itemsets_list


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train FP-Growth phishing pattern miner (InvisiPhish Phase 1)"
    )
    parser.add_argument(
        "--min_support",
        type=float,
        default=DEFAULT_MIN_SUPPORT,
        help=f"Minimum support threshold σ (paper default: {DEFAULT_MIN_SUPPORT})",
    )
    args = parser.parse_args()
    train(args.min_support)
