import re

def clean_message(text):
    """Cleans input message while preserving useful punctuation for sentiment analysis."""
    if not text:
        return "", []

    # Convert to lowercase
    text = text.lower().strip()

    # ✅ Improved URL Regex to detect:
    url_regex = r'https?://\S+|www\.\S+|\b[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
    
    # Extract URLs (including links without http/https)
    urls = re.findall(url_regex, text)

    # Remove detected URLs from text
    text_without_urls = re.sub(url_regex, '', text)

    # Remove emojis (Unicode characters beyond ASCII)
    text_without_urls = re.sub(r'[^\x00-\x7F]+', '', text_without_urls)

    # Keep single occurrences of !, ?, .
    text_without_urls = re.sub(r'([!?.,])\1+', r'\1', text_without_urls)

    # Remove all other special characters (except !, ?, . for sentiment analysis)
    text_without_urls = re.sub(r'[^a-zA-Z0-9\s!?.,]', '', text_without_urls)

    # Normalize spaces
    text_without_urls = re.sub(r'\s+', ' ', text_without_urls).strip()

    return text_without_urls, urls

def preprocess_message(message_data):
    """Preprocess SMS & Email messages in a unified way."""
    message_type = message_data.get("message_type")
    sender = None
    message_body, subject, all_links = "", "", []

    if message_type == "email":
        # Process Email
        message_body = message_data.get("message", "")
        subject = message_data.get("email_subject", "")
        sender = message_data.get("sender_email", "")

    elif message_type == "sms":
        # Process SMS
        message_body = message_data.get("message", "")
        sender = message_data.get("sender_number", "")

    # Clean & extract links
    cleaned_body, body_links = clean_message(message_body)
    cleaned_subject, subject_links = clean_message(subject) if subject else ("", [])
    
    # Merge all links
    all_links = list(set(body_links + subject_links))

    # Final structured output
    return {
        "message_type": message_type,
        "cleaned_body": cleaned_body,
        "cleaned_subject": cleaned_subject if subject else None,
        "sender": sender,
        "links": all_links
    }
