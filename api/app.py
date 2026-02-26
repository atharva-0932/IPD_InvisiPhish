# app.py
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import logging

# Ensure the package path imports your existing modules
# If your backend is a package, use relative imports. Otherwise adapt the import paths.
from .deeplearning import get_dl_phishing_score  # updated module
from .fpgrowth import process_message
from .preprocess import preprocess_message, clean_message
from .sentiment import classify_intent_zero_shot
from .genai import generate as genai_generate
from .database import store_message  # uses Supabase but optional

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Local Phishing Classifier API")

class ClassifyRequest(BaseModel):
    message_type: str  # "email" or "sms"
    message: str = None
    email_subject: str = None
    email_body: str = None
    sender_number: str = None
    sender_email: str = None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/classify")
def classify(req: ClassifyRequest):
    try:
        # Validate and normalize
        mtype = req.message_type
        if mtype not in ("email", "sms"):
            raise HTTPException(status_code=400, detail="message_type must be 'email' or 'sms'")

        # Build full_text similar to your routes.py logic
        if mtype == "sms":
            full_text = req.message or ""
            sender_info = req.sender_number or "Unknown"
        else:
            subj = req.email_subject or ""
            body = req.email_body or req.message or ""
            full_text = f"{subj} {body}".strip()
            sender_info = req.sender_email or "Unknown"

        # Preprocess
        processed = preprocess_message({
            "message_type": mtype,
            "message": req.message,
            "email_subject": req.email_subject,
            "email_body": req.email_body,
            "sender_number": req.sender_number,
            "sender_email": req.sender_email
        })

        # FP-Growth analysis (your existing function)
        fp = process_message(
            message_type=mtype,
            original_text=req.message if mtype == "sms" else None,
            email_subject=req.email_subject if mtype == "email" else None,
            email_body=req.email_body if mtype == "email" else None
        )
        fp_score = fp.get("final_score", 0)

        # Deep Learning score (updated get_dl_phishing_score)
        dl_score = get_dl_phishing_score(full_text)

        # Sentiment / intent
        try:
            sentiment = classify_intent_zero_shot(full_text)
            intent_label = list(sentiment.keys())[0] if sentiment else "Neutral"
            sentiment_score = list(sentiment.values())[0] if sentiment and intent_label != "Neutral" else 0
        except Exception as e:
            intent_label = "Neutral"
            sentiment_score = 0

        # GenAI
        try:
            genai_result = genai_generate(full_text)
            genai_score = genai_result.get("phishing_score", 0)
            genai_explanation = genai_result.get("explanation", "")
        except Exception as e:
            genai_score = 0
            genai_explanation = f"GenAI error: {e}"

        # Combined score (keep your original weights from routes.py)
        combined_score = round(
            (fp_score * 0.15) +
            (dl_score * 0.15) +
            (sentiment_score * 0.30) +
            (genai_score * 0.40),
            2
        )

        final_result = "Phishing" if 41 <= combined_score <= 100 else "Legitimate"
        risk_level = "High Risk" if combined_score >= 70 else ("Medium Risk" if combined_score >= 41 else "Low Risk")

        response = {
            "success": True,
            "message_type": mtype,
            "sender": sender_info,
            "analysis": {
                "final_score": combined_score,
                "final_result": final_result,
                "risk_level": risk_level,
                "scores_breakdown": {
                    "fp_growth": {"score": fp_score, "keywords": fp.get("extracted_keywords", [])},
                    "deep_learning": {"score": dl_score},
                    "sentiment": {"score": sentiment_score, "intent": intent_label},
                    "genai": {"score": genai_score, "explanation": genai_explanation}
                },
                "preprocessing": {
                    "cleaned_subject": processed.get("cleaned_subject", ""),
                    "cleaned_body": processed.get("cleaned_body", ""),
                    "links_found": processed.get("links", [])
                }
            }
        }

        # Optional: store message in DB if Supabase is configured
        try:
            store_message(
                message_type=mtype,
                original_text=req.message if mtype == "sms" else (req.email_body or req.message),
                sender_number=req.sender_number,
                email_subject=req.email_subject,
                email_body=req.email_body or req.message,
                sender_email=req.sender_email,
                genai_feedback=genai_explanation,
                cleaned_subject=processed.get("cleaned_subject"),
                cleaned_body=processed.get("cleaned_body"),
                links=processed.get("links"),
                fp_score=fp_score,
                dl_score=dl_score,
                sentiment_score=sentiment_score,
                genai_score=genai_score,
                intent_label=intent_label,
                extracted_keywords=fp.get("extracted_keywords", [])
            )
        except Exception as e:
            # do not fail the call if DB fails; just log
            logging.warning(f"store_message failed: {e}")

        return response

    except HTTPException as he:
        raise he
    except Exception as e:
        logging.exception("Error in /classify")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # By default run on port 5000 to match extension code
    # Run target is the package path so uvicorn finds the app when invoked as a package
    # Disable auto-reload by default to avoid reload loops caused by model downloads
    # Set environment variable RELOAD=true to enable reload when actively developing
    reload_flag = os.environ.get("RELOAD", "false").lower() in ("1", "true", "yes")
    uvicorn.run(
        "api.app:app",
        host="127.0.0.1",
        port=int(os.environ.get("PORT", 5000)),
        reload=reload_flag,
    )
