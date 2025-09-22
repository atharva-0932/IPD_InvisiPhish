from flask import Blueprint, request, jsonify
from .database import store_message, get_messages
from .preprocess import preprocess_message
from .preprocess import clean_message
from .fpgrowth import process_message
from .deeplearning import get_dl_phishing_score
from .sentiment import classify_intent_zero_shot
from .genai import generate
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

@routes.route('/analyze_message', methods=['POST'])
def analyze_message():
    """
    Comprehensive endpoint to analyze a message for phishing detection.
    Performs all analysis (FP-Growth, Deep Learning, Sentiment, GenAI) 
    and returns complete results with proper scoring weights.
    """
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Invalid request data"}), 400
        
        # Get message type and content
        message_type = data.get("message_type")
        if not message_type or message_type not in ["sms", "email"]:
            return jsonify({"error": "Invalid message_type. Use 'sms' or 'email'."}), 400
        
        # Extract message content based on type
        if message_type == "sms":
            message_text = data.get("message")
            if not message_text:
                return jsonify({"error": "SMS message is required"}), 400
            full_text = message_text
            sender_info = data.get("sender_number", "Unknown")
        else:  # email
            email_subject = data.get("email_subject", "")
            email_body = data.get("message", data.get("email_body", ""))
            if not email_subject and not email_body:
                return jsonify({"error": "Email subject or body is required"}), 400
            full_text = f"{email_subject} {email_body}"
            sender_info = data.get("sender_email", "Unknown")
        
        # 1. Preprocess the message
        processed_data = preprocess_message(data)
        
        # 2. FP-Growth Analysis (15% weight)
        fp_growth_result = process_message(
            message_type=message_type,
            original_text=data.get("message") if message_type == "sms" else None,
            email_subject=data.get("email_subject") if message_type == "email" else None,
            email_body=data.get("message") if message_type == "email" else None
        )
        fp_score = fp_growth_result["final_score"]
        
        # 3. Deep Learning Analysis (15% weight)
        dl_score = get_dl_phishing_score(full_text)
        
        # 4. Sentiment/Intent Analysis (30% weight)
        sentiment_result = classify_intent_zero_shot(full_text)
        intent_label = list(sentiment_result.keys())[0] if sentiment_result else "Neutral"
        sentiment_score = list(sentiment_result.values())[0] if sentiment_result else 0
        
        # 5. GenAI Analysis - Gemini (40% weight)
        try:
            genai_result = generate(full_text)
            genai_score = genai_result.get("phishing_score", 0)
            genai_explanation = genai_result.get("explanation", "No explanation available")
        except Exception as e:
            print(f"GenAI error: {str(e)}")
            genai_score = 0
            genai_explanation = "GenAI analysis unavailable"
        
        # Calculate combined score using database weights:
        # FP-Growth: 15%, Deep Learning: 15%, Sentiment: 30%, GenAI: 40%
        combined_score = round(
            (fp_score * 0.15) +           # 15% weight for FP-Growth
            (dl_score * 0.15) +           # 15% weight for Deep Learning 
            (sentiment_score * 0.30) +    # 30% weight for Sentiment
            (genai_score * 0.40),         # 40% weight for GenAI
            2
        )
        
        # Determine overall risk level (matching database logic)
        if combined_score >= 41 and combined_score <= 100:
            final_result = "Phishing"
            risk_level = "High Risk" if combined_score >= 70 else "Medium Risk"
            risk_color = "red" if combined_score >= 70 else "yellow"
        else:
            final_result = "Legitimate"
            risk_level = "Low Risk"
            risk_color = "green"
        
        # Prepare comprehensive response
        analysis_result = {
            "success": True,
            "message_type": message_type,
            "sender": sender_info,
            "analysis": {
                "final_score": combined_score,
                "final_result": final_result,
                "risk_level": risk_level,
                "risk_color": risk_color,
                "scores_breakdown": {
                    "fp_growth": {
                        "score": fp_score,
                        "weight": "15%",
                        "weighted_score": round(fp_score * 0.15, 2),
                        "classification": fp_growth_result["final_result"],
                        "keywords": fp_growth_result["extracted_keywords"]
                    },
                    "deep_learning": {
                        "score": dl_score,
                        "weight": "15%",
                        "weighted_score": round(dl_score * 0.15, 2),
                        "confidence": f"{dl_score}%"
                    },
                    "sentiment": {
                        "score": sentiment_score,
                        "weight": "30%",
                        "weighted_score": round(sentiment_score * 0.30, 2),
                        "intent": intent_label,
                        "intent_details": sentiment_result
                    },
                    "genai": {
                        "score": genai_score,
                        "weight": "40%",
                        "weighted_score": round(genai_score * 0.40, 2),
                        "explanation": genai_explanation
                    }
                },
                "preprocessing": {
                    "cleaned_subject": processed_data.get("cleaned_subject", ""),
                    "cleaned_body": processed_data.get("cleaned_body", ""),
                    "links_found": processed_data.get("links", [])
                }
            },
            "recommendations": generate_recommendations(combined_score, final_result, processed_data.get("links", []))
        }
        
        # Store the analysis in database
        store_result = store_message(
            message_type=message_type,
            original_text=data.get("message"),
            sender_number=data.get("sender_number") if message_type == "sms" else None,
            email_subject=data.get("email_subject") if message_type == "email" else None,
            email_body=data.get("message") if message_type == "email" else None,
            sender_email=data.get("sender_email") if message_type == "email" else None,
            genai_feedback=genai_explanation,
            cleaned_subject=processed_data.get("cleaned_subject"),
            cleaned_body=processed_data.get("cleaned_body"),
            links=processed_data.get("links"),
            fp_score=fp_score,
            dl_score=dl_score,
            sentiment_score=sentiment_score,
            genai_score=genai_score,
            intent_label=intent_label,
            extracted_keywords=fp_growth_result["extracted_keywords"]  # Pass keywords
        )
        
        # Add database ID to response, with proper error handling
        if store_result and hasattr(store_result, 'data') and store_result.data:
            analysis_result["message_id"] = store_result.data[0].get("id") if isinstance(store_result.data, list) else store_result.data.get("id")
        elif store_result and store_result.get("error"):
            print(f"Failed to store message in database: {store_result.get('error')}")
            # Optionally, you can add this error to the response sent to the frontend
            analysis_result["database_error"] = f"Could not save results: {store_result.get('error')}"
        
        return jsonify(analysis_result)
        
    except Exception as e:
        print(f"Error in analyze_message: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

def generate_recommendations(score, result, links):
    """Generate security recommendations based on analysis results"""
    recommendations = []
    
    if result == "Phishing":
        if score >= 70:
            recommendations.extend([
                "⚠️ HIGH RISK: This message is very likely a phishing attempt",
                "🚫 DO NOT click any links in this message",
                "🛑 DO NOT provide any personal information",
                "🗑️ Delete this message immediately",
                "📧 Report as phishing to your email/SMS provider",
                "🔒 If you already clicked links, change your passwords immediately"
            ])
        else:  # Medium risk (41-69)
            recommendations.extend([
                "⚠️ MEDIUM RISK: This message shows signs of phishing",
                "🔍 Verify sender through official channels",
                "🚫 Avoid clicking suspicious links",
                "📞 Contact the company directly if unsure",
                "⚡ Do not provide sensitive information"
            ])
    else:  # Legitimate
        recommendations.extend([
            "✅ Message appears to be legitimate",
            "👀 Still verify sender if unexpected",
            "🔒 Always be cautious with personal information",
            "💡 Remember: legitimate companies won't ask for passwords via email/SMS"
        ])
    
    if links and len(links) > 0:
        recommendations.append(f"🔗 Found {len(links)} link(s) - always verify URLs before clicking")
    
    return recommendations
