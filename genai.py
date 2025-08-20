import os
from google import genai
from google.genai import types
import json
from dotenv import load_dotenv
load_dotenv()
def generate(input_text):
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    model = "gemini-2.0-flash"

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=input_text)],
        ),
    ]

    generate_content_config = types.GenerateContentConfig(
        temperature=0.6,
        response_mime_type="application/json",
        system_instruction=[
            types.Part.from_text(text="""
            You are an expert in cybersecurity and social engineering detection, specializing in phishing, scams, and fraud identification. You analyze messages rationally, considering all possibilities before concluding.

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

    # Convert response text to JSON
    try:
        response_json = json.loads(response_text)  # Ensure it's a valid JSON
    except json.JSONDecodeError:
        response_json = {"phishing_score": 0, "explanation": "Invalid response from AI"}

    return response_json  # Return JSON object
