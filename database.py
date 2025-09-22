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

def store_message(
    message_type,
    original_text,
    sender_number,
    email_subject,
    email_body,
    sender_email,
    genai_feedback,
    cleaned_subject,
    cleaned_body,
    links,
    fp_score,
    dl_score,
    sentiment_score,
    genai_score,
    intent_label,
    extracted_keywords  # Added to accept keywords
):
    """
    Stores a message and its analysis results in the database, matching the specific
    schema provided by the user.
    """
    try:
        # Use the pre-calculated scores passed as arguments
        fp_growth_score = fp_score
        deep_learning_score = dl_score
        sentiment_analysis_score = sentiment_score
        genai_score_val = genai_score

        # Calculate the combined score using the provided scores and defined weights
        combined_score = round(
            (fp_growth_score * 0.15) +
            (deep_learning_score * 0.15) +
            (sentiment_analysis_score * 0.30) +
            (genai_score_val * 0.40),
            2
        )

        # Determine final result
        final_result = "Phishing" if 41 <= combined_score <= 100 else "Legitimate"

        # Analyze sender details
        sender_risk = analyze_sender_number(sender_number) if message_type == "sms" else "N/A"
        email_risk = analyze_sender_email(sender_email) if message_type == "email" else "N/A"

        # Prepare data for Supabase, matching the user's schema from the image
        data_to_insert = {
            "message_type": message_type,
            "original_text": original_text,
            "sender_number": sender_number,
            "sender_email": sender_email,
            "email_subject": email_subject,
            "email_body": email_body,
            "cleaned_subject": cleaned_subject,
            "cleaned_body": cleaned_body,
            "links": links,
            "extracted_keywords": extracted_keywords,  # Matches 'extracted_key' column
            "email_risk_level": email_risk,         # Matches 'email_risk_lev' column
            "sender_number_risk": sender_risk,           # Matches 'sender_numb' column
            "final_score": combined_score,        # Matches 'final_score' column
            "final_result": final_result,         # Matches 'final_result' column
            "genai_feedback": genai_feedback,     # Matches 'genai_feedback' column
            "intent_label": intent_label          # Matches 'intent_label' column
        }

        # Insert data into Supabase
        response = supabase.table("messages").insert(data_to_insert).execute()

        # Check for successful insertion (status code 201 means 'Created')
        if response.status_code == 201 and response.data:
            print("Successfully inserted data into Supabase.")
            return response
        else:
            # Provide detailed error logging if insertion fails
            print(f"Error inserting data into Supabase. Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
            return {"error": f"Failed to insert data. Status: {response.status_code}"}

    except Exception as e:
        print(f"Error in store_message: {e}")
        return {"error": str(e)}

def get_messages():
    """Retrieve all stored messages from Supabase."""
    return supabase.table("messages").select("*").execute()
