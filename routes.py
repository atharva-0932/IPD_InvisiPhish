from flask import Blueprint, request, jsonify
from database import store_message, get_messages
from preprocess import preprocess_message
from preprocess import clean_message
from fpgrowth import process_message
from deeplearning import get_dl_phishing_score
from sentiment import classify_intent_zero_shot
from genai import generate
routes = Blueprint("routes", __name__)

@routes.route('/store_message', methods=['POST'])
def store_message_route():
    """
    Store a new SMS or Email message, process it using FP-Growth & NLP,
    and store the extracted phishing-related data into Supabase.
    """
    data = request.json
    if not data:
        return jsonify({"error": "Invalid request data"}), 400

    # Retrieve message_type first to avoid UnboundLocalError
    message_type = data.get("message_type")
    if not message_type:
        return jsonify({"error": "Message type is required"}), 400
    processed_data = preprocess_message(data)
    # Retrieve message based on type
    message = data.get("message") if message_type == "sms" else None
    email_subject = data.get("email_subject") if message_type == "email" else None
    email_body = data.get("email_body") if message_type == "email" else None
    sender_number = data.get("sender_number") if message_type == "sms" else None
    sender_email = data.get("sender_email") if message_type == "email" else None

    response = store_message(
        message_type=processed_data["message_type"],
        original_text=data.get("message"),
        sender_number=data.get("sender_number"),
        email_subject=data.get("email_subject"),
        email_body=data.get("message"),
        sender_email=data.get("sender_email"),
        genai_feedback=None,
        cleaned_subject=processed_data["cleaned_subject"],
        cleaned_body=processed_data["cleaned_body"],
        links=processed_data["links"]
    )

    return jsonify({"success": True, "data": response.data})



@routes.route('/get_messages', methods=['GET'])
def get_messages_route():
    """Retrieve all stored messages from the database."""
    response = get_messages()
    return jsonify(response.data)

