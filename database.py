import os
import re
from supabase import create_client
from dotenv import load_dotenv
from preprocess import preprocess_message
from fpgrowth import process_message
from deeplearning import get_dl_phishing_score
from sentiment import classify_intent_zero_shot
from genai import generate
# Load environment variables
load_dotenv()

# Get Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
# Ensure credentials are loaded correctly
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials are missing! Check .env file.")

# Connect to Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def analyze_sender_email(email):
    """Analyze sender email for phishing risk."""
    if not email:
        return "unknown"
    domain = email.split("@")[-1].lower()
    free_email_providers = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com"}
    if domain in free_email_providers:
        return "freemail"
    suspicious_patterns = ["verify", "secure", "update", "support", "customer", "service"]
    if any(pattern in domain for pattern in suspicious_patterns):
        return "suspicious"
    return "legit"

def analyze_sender_number(sender):
    """Analyze SMS sender to check if it's a normal number or an alphanumeric ID."""
    if not sender:
        return "unknown"
    if sender.isalpha() or "-" in sender:
        return "legit"
    if sender.isdigit() and (4 <= len(sender) <= 6):
        return "legit"
    return "suspicious"

def store_message(message_type, original_text=None, sender_number=None, email_subject=None, email_body=None, sender_email=None,cleaned_subject=None, cleaned_body=None, links=None, genai_feedback=None):
    """
    Store SMS or Email message, extract features using FP-Growth & Deep Learning,
    and store the final risk assessment in Supabase.
    """
    # Process with FP-Growth
    result = process_message(message_type, original_text, email_subject, email_body)
    fp_score = result.get("final_score")

    # Process with Deep Learning
    text = original_text if message_type == "sms" else f"{email_subject or ''} {email_body or ''}"
    dl_score = get_dl_phishing_score(text)

    # Process with Sentiment Analysis
    text = original_text if message_type == "sms" else f"{email_subject or ''} {email_body or ''}"
    sentiment_result = classify_intent_zero_shot(text)
    intent_label = list(sentiment_result.keys())[0]
    sentiment_score = list(sentiment_result.values())[0]
    # Getting output from GenAI
    genai_result = generate(f"Message: {original_text}\nSender Number: {sender_number}")
    genai_score = genai_result.get("phishing_score", 0)
    genai_feedback = genai_result.get("explanation", "No explanation provided")
    # ✅ Compute final averaged score
    final_score = round((fp_score * 0.15) + (dl_score * 0.15) + (sentiment_score*0.30) + (genai_score*0.40), 2) 

    # ✅ Determine final classification based on threshold
    if final_score >= 41 and final_score <= 100:
        final_result = "Phishing"
    else:
        final_result = "Legitimate"
    processed_data = preprocess_message({
        "message_type": message_type,
        "message": original_text if message_type == "sms" else email_body,
        "email_subject": email_subject,
        "sender_email": sender_email,
        "sender_number": sender_number
    })
    
    cleaned_body = processed_data.get("cleaned_body", "")  # Default to empty string if missing
    cleaned_subject = processed_data.get("cleaned_subject", "")  # Default to empty string if missing
    links = processed_data.get("links", [])  # Default to empty list if missing
    sender_email = processed_data.get("sender_email", sender_email if message_type == "email" else None)
    sender_number = processed_data.get("sender_number", sender_number if message_type == "sms" else None)  # Default sender
    # Process SMS messages
    if message_type == "sms":
        
        data = {
            "message_type": "sms",
            "original_text": original_text,
            "sender_number": sender_number,
            "sender_number_risk": analyze_sender_number(sender_number) if sender_number else None,
            "cleaned_subject": None,
            "cleaned_body": None,
            "sender_email": None,
            "email_risk_level": None,
            "links": links,
            "extracted_keywords": result.get("extracted_keywords"),
            "intent_label": intent_label,
            "final_score": final_score,
            "final_result": final_result,
            "genai_feedback": genai_feedback
        }
    # Process Email messages
    elif message_type == "email":
        data = {
            "message_type": "email",
            "email_subject": email_subject,
            "email_body": email_body,
            "cleaned_subject": cleaned_subject,
            "cleaned_body": cleaned_body,
            "sender_email": sender_email,
            "email_risk_level": analyze_sender_email(sender_email) if sender_email else None,
            "sender_number": None,
            "sender_number_risk": None,
            "links": links,
            "extracted_keywords": result.get("extracted_keywords"),
            "intent_label": intent_label,
            "final_score": final_score,
            "final_result": final_result,
            "genai_feedback": genai_feedback
        }
    return supabase.table("messages").insert(data).execute()

def get_messages():
    """Retrieve all stored messages from Supabase."""
    return supabase.table("messages").select("*").execute()
