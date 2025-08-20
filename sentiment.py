from transformers import pipeline

# Load zero-shot classification model

def classify_intent_zero_shot(text, confidence_threshold=0.15):
    """
    Classifies the input text into the most relevant intent category.
    - confidence_threshold: Lowered to 0.15 to capture more nuanced intents.
    - Returns only the highest confidence intent.
    """
    classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

# ✅ **Intent Labels**
    candidate_labels = ["Urgency", "Fear", "Scarcity", "Authority", "Reward", "Suspicion", "Neutral"]
    if not text or text.strip() == "":
        return 0
    result = classifier(text, candidate_labels)
    labels, scores = result["labels"], result["scores"]

    # Normalize scores
    total_score = sum(scores)
    normalized_scores = [s / total_score for s in scores]

    # Pair labels with normalized scores
    filtered_labels = [(label, score) for label, score in zip(labels, normalized_scores) if score >= confidence_threshold]

    # If no intent meets the threshold, return "Neutral" with low confidence
    if not filtered_labels:
        return {"Neutral": 10.0}

    # Select the **highest confidence** intent
    best_intent, best_score = max(filtered_labels, key=lambda x: x[1])
    return {best_intent: round(best_score * 100, 2)}

