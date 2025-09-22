import torch
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
import torch.nn.functional as F

# Load the pre-trained tokenizer and model (replace with fine-tuned model if available)
MODEL_NAME = "distilbert-base-uncased"
tokenizer = DistilBertTokenizer.from_pretrained(MODEL_NAME)
model = DistilBertForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=2)  # 2 classes: Legit or Phishing

# Ensure model is in evaluation mode
model.eval()

# --------------------------
# Function: Get Deep Learning Phishing Score
# --------------------------
def get_dl_phishing_score(text):
    """
    Uses DistilBERT to classify a message as phishing or legitimate.
    Returns a phishing confidence score (0-100).
    """
    if not text or text.strip() == "":
        return 0  # Empty messages are safe

    # Tokenize input text & convert to tensors
    inputs = tokenizer(text, padding=True, truncation=True, return_tensors="pt")
    
    with torch.no_grad():  # Disable gradient computation (inference mode)
        outputs = model(**inputs)
    
    # Get predicted probabilities (softmax activation)
    probabilities = F.softmax(outputs.logits, dim=-1)
    phishing_score = probabilities[0][1].item() * 100  # Convert to percentage (0-100)

    return round(phishing_score, 2) 


if __name__ == "__main__":
    test_sms = "URGENT! Your bank account is at risk. Click here to verify now!"
    score = get_dl_phishing_score(test_sms)
    print(f"DistilBERT Phishing Score: {score}%")
