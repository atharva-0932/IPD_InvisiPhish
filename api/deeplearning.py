# deeplearning.py
import os
import torch
import logging
import torch.nn.functional as F
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification

logging.basicConfig(level=logging.INFO)

# Look for a local fine-tuned model first
LOCAL_MODEL_DIR = os.path.join(os.path.dirname(__file__), "models", "distilbert_saved")
FALLBACK_MODEL_NAME = "distilbert-base-uncased"

def load_model_and_tokenizer():
    try:
        if os.path.exists(LOCAL_MODEL_DIR) and os.path.isdir(LOCAL_MODEL_DIR):
            logging.info(f"Loading local DistilBERT model from {LOCAL_MODEL_DIR}")
            tokenizer = DistilBertTokenizer.from_pretrained(LOCAL_MODEL_DIR)
            model = DistilBertForSequenceClassification.from_pretrained(LOCAL_MODEL_DIR)
        else:
            logging.info(f"Local model not found. Loading pre-trained '{FALLBACK_MODEL_NAME}' from HuggingFace.")
            tokenizer = DistilBertTokenizer.from_pretrained(FALLBACK_MODEL_NAME)
            model = DistilBertForSequenceClassification.from_pretrained(FALLBACK_MODEL_NAME, num_labels=2)
        model.eval()
        return tokenizer, model
    except Exception as e:
        logging.exception("Failed to load DL model/tokenizer")
        raise e

# Load at import time
try:
    tokenizer, model = load_model_and_tokenizer()
except Exception as e:
    # If loading fails, set to None and handle in scoring function
    tokenizer, model = None, None

def get_dl_phishing_score(text):
    """
    Returns a 0-100 phishing confidence score using DistilBERT.
    If model/tokenizer failed to load, returns 0 and logs the error.
    """
    try:
        if not text or text.strip() == "":
            return 0.0
        if tokenizer is None or model is None:
            logging.warning("DL model/tokenizer not loaded; returning 0 for dl_score")
            return 0.0

        # Ensure input length is reasonable
        inputs = tokenizer(text, padding=True, truncation=True, return_tensors="pt", max_length=256)
        with torch.no_grad():
            outputs = model(**inputs)
        probs = torch.softmax(outputs.logits, dim=-1)[0]
        phishing_score = float(probs[1].item() * 100)
        return round(phishing_score, 2)
    except Exception as e:
        logging.exception("Error computing DL phishing score")
        return 0.0

# Simple test when run directly
if __name__ == "__main__":
    test = "URGENT! Verify your account here: http://phishy.example.com"
    print("DL score:", get_dl_phishing_score(test))

