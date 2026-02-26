import os
from google import genai
from google.genai import types
import json
from dotenv import load_dotenv
load_dotenv()
def generate(input_text, message_type, sender_email=None, email_subject=None, sender_number=None):
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    model = "gemini-2.5-flash"
    if message_type == "sms":
        combined_input = f"""
Message Body:
{input_text}

Sender Number: {sender_number}
"""
    elif message_type == "email":
        combined_input = f"""
Message Body:
{input_text}

Sender Email: {sender_email}
Email Subject: {email_subject}
"""
    else:
        combined_input = input_text  # fallback if message_type is unknown

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=combined_input)],
        ),
    ]

    generate_content_config = types.GenerateContentConfig(
        temperature=0.6,
        response_mime_type="application/json",
        system_instruction=[
            types.Part.from_text(text="""
            You are an expert in cybersecurity and social engineering detection, specializing in phishing, scams, and fraud identification. You do not over-analyze messages, there might be messages or emails which are completely legitimate, such messages or emails do not require extensive analysis, so make sure to adjust your scoring to be as low as possible for a legitimate message. You also analyze messages & emails rationally, considering all possibilities before concluding.

            ## 🛠 Scoring Considerations:
            1️⃣ **Legitimate Messages (0-40 Score)**
                - Sent by a well-known company.
                - Provides a **reminder** (e.g., "Your subscription payment failed").
                - **No direct login link**.
                - Uses **official domain**.
                - Messages from **friends or known persons**.

            2️⃣ **Medium-Risk Phishing (41-65 Score)**
                - **Generic warnings** (e.g., "Your account has a problem").
                - Uses **urgent language** but no strong threat.
                - Mentions **refunds, billing issues, or verification**.

            3️⃣ **High-Risk Phishing (66-100 Score)**
                - **Strong urgency & fear tactics** (e.g., "Act immediately or be locked out").
                - **Fake domains** (e.g., secure-paypal-billing.com instead of paypal.com).
                - **Requests personal info, passwords, or credit card details**.
                - **Tries to impersonate a trusted authority**.

            ## 📌 Response Format:
            - Provide a **phishing score** (0-100) based on the analysis.
            - Provide a **detailed text response** explaining the classification.
            - Mention **specific words, tone, deception tactics, and domain legitimacy**.
            - Offer **tips to detect and avoid phishing**.
            -You MUST return valid JSON with EXACTLY the following keys.
            DO NOT add, rename, or remove keys.

            {
                "phishing_score": number,               // integer 0–100
                "explanation": string                   // detailed human-readable explanation
            }
            """),
        ],
    )

    response_text = ""  # Collect response text

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        if chunk.text:
            response_text += chunk.text
    
    response_text=response_text.strip()

    # Convert response text to JSON
    try:
        response_json = json.loads(response_text)  # Ensure it's a valid JSON
    except json.JSONDecodeError:
        response_json = {"phishing_score": 0, "explanation": "Invalid response from AI"}

    return response_json  # Return JSON object