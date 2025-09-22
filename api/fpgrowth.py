import os
import re
import nltk
import spacy
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import CountVectorizer

# --------------------------
# Load NLP Resources
# --------------------------
nltk.download('stopwords')
nltk.download('wordnet')
nlp = spacy.load("en_core_web_sm")
lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words("english"))

HIGH_RISK_KEYWORDS = {"password", "login", "verify", "account", "fraud", "bank", "security", "breach",
    "credential", "authentication", "personal", "identity", "compromise", "unauthorized",
    "transaction", "verification", "restricted", "confidential", "malware", "spyware",
    "ransomware", "OTP", "debit", "credit", "billing", "statement", "scam", "hijack",
    "access denied", "locked account", "phishing", "data theft", "stolen", "blacklisted",
    "unusual activity", "privacy alert", "wire transfer", "unauthorized payment",
    "identity theft", "emergency", "recovery", "breached", "security alert",
    "banking", "secure", "verified", "account locked", "suspicious login", "sensitive",
    "login failure", "security breach", "unauthorized login", "reset password",
    "login credentials", "account compromised", "data leak", "cyber attack", "fraudulent",
    "fraud alert", "suspicious transaction", "financial alert", "immediate action",
    "credit freeze", "cvv", "pin", "2fa", "mfa", "compromised account", "internet banking",
    "secret question", "password reset", "new login", "suspicious activity", "verify identity",
    "data breach", "security compromise", "counterfeit", "scammer", "phish", "spoof", "fake email",
    "critical update", "immediate verification", "sensitive information", "access violation",
    "account alert", "security notification", "system breach", "network intrusion", "unauthorized access",
    "data interception", "password compromise", "credential exposure", "system hack", "malicious link",
    "dangerous attachment", "email spoofing", "session hijack", "remote access", "keylogger detected",
    "unauthorized download", "virus detected", "trojan", "worm", "spyware alert", "intrusion detected",
    "incident report", "security warning", "compromise detected", "data corruption", "network breach",
    "unauthorized modification", "suspicious file", "infected", "malicious code", "denial of service",
    "exploit", "backdoor", "unauthorized device", "system exploit", "password breach", "credential hack",
    "fraud detection", "risk detected", "security incident", "hacker", "cyber threat", "malicious activity",
    "exploit attempt", "security flaw", "encrypted breach", "compromised data", "unauthorized user",
    "illegal access", "security violation", "network compromise", "unauthorized change", "sensitive data leak",
    "credential breach", "user data exposed", "financial compromise", "unauthorized funds transfer",
    "unapproved access", "security override", "critical alert", "immediate response", "elevated risk",
    "compromised network", "unauthorized transaction", "illegal transaction", "security override",
    "multi-factor bypass", "phishing link", "malicious URL", "fraud link", "spoofed website",
    "fake login page", "credential harvesting", "compromised credentials", "bank alert", "fraudulent activity",
    "data compromise", "security breach notification", "cyber breach", "targeted attack", "APT detected",
    "advanced persistent threat", "brute force", "password cracking", "encrypted phishing", "unauthorized clearance",
    "illegal operation", "risky login", "suspicious operation", "forged email", "counterfeit alert",
    "discrepancy", "unauthorized access attempt", "suspicious IP", "untrusted device", "phishing attack",
    "malware infection", "cyber fraud", "account takeover", "impersonation", "spoofing attack",
    "digital fraud", "pharming", "session fixation", "credential stuffing", "botnet", "cyber scam",
    "phishing scam", "zero-day exploit", "data exfiltration", "security gap", "information leak",
    "password leak", "data dump", "database breach", "compromised database", "security incident response",
    "phishing website", "fraudulent website", "impersonated", "unauthorized entry", "security compromise",
    "data interception", "account misuse", "security risk", "login anomaly", "credential misuse",
    "abnormal access", "unauthorized operation", "critical vulnerability", "vulnerability exploited",
    "network vulnerability", "identity fraud", "suspicious credentials", "phishing notification",
    "suspicious password", "improper access", "access breach", "security exploit", "intrusion prevention",
    "malicious domain", "spoofed domain", "fraudulent login", "unauthorized attempt", "incident detected",
    "security failure", "unauthorized system", "malicious behavior", "phishing detection", "email compromise",
    "spoofed message", "system integrity", "integrity breach", "breach report", "unauthorized alert",
    "unauthorized alert system", "cyber intrusion", "fraudulent alert", "risk management breach"}
MEDIUM_RISK_KEYWORDS = {"alert", "access", "confirm", "update", "reset", "warning", "suspicious", "refund",
    "urgent", "notify", "dispute", "update required", "locked", "reactivate", "payment",
    "unpaid", "overdue", "penalty", "assistance", "issue", "subscription", "renewal",
    "invoice", "pending", "troubleshoot", "security check", "customer support", "maintenance",
    "contact support", "verify now", "password change", "restricted access", "customer care",
    "technical support", "system update", "login attempt", "recovery code", "request submitted",
    "notification", "reminder", "verification required", "service disruption", "pending update",
    "pending payment", "information update", "suspicious behavior", "client alert",
    "account notice", "system maintenance", "billing reminder", "activity alert",
    "order update", "delivery notification", "invoice update", "fraud notice", "account verification",
    "update immediately", "support ticket", "email alert", "service alert", "update notification",
    "system alert", "user alert", "information alert", "account update", "transaction alert",
    "payment reminder", "support alert", "customer notice", "service notice", "alert notification",
    "maintenance update", "operational alert", "issue detected", "support required", "warning sign",
    "technical alert", "disruption notice", "operational update", "critical update notice",
    "service interruption", "account flag", "alert system", "security notice", "risk alert",
    "account recovery", "profile update", "renewal required", "verification pending", "billing update",
    "service renewal", "account monitoring", "activity notice", "data update", "security advisory",
    "system notification", "customer inquiry", "pending verification", "update pending",
    "support follow-up", "action required", "contact required", "account discrepancy", "info mismatch",
    "unresolved issue", "system check", "routine maintenance", "service check", "security patch",
    "notification required", "process update", "payment processing", "payment delay",
    "support response", "user inquiry", "pending confirmation", "temporary suspension",
    "account review", "support followup", "billing query", "payment inquiry", "account audit",
    "account warning", "profile verification", "security update", "system refresh", "information check",
    "data integrity check", "verification alert", "account advisory", "system advisory", "account prompt",
    "subscription renewal notice", "service update", "operational update", "software update",
    "maintenance window", "scheduled maintenance", "unusual activity notice", "support update",
    "status update", "pending adjustments", "verification process", "customer feedback",
    "account status", "service feedback", "support inquiry", "account notice update", "system reminder",
    "communication update", "billing communication", "customer notification", "system communication",
    "transaction update", "payment status", "verification initiated", "update in process",
    "critical notification", "service error", "login reminder", "credential update", "profile correction",
    "system verification", "support escalation", "account escalation", "process pending", "document update"}
LOW_RISK_KEYWORDS = {"click", "free", "offer", "limited", "prize", "winner", "claim", "congratulations",
    "lucky", "lottery", "jackpot", "bonus", "exclusive", "trial", "cash", "cheap",
    "investment", "discount", "deal", "coupon", "gift", "reward", "promo", "unlimited",
    "guarantee", "special", "savings", "extra bonus", "double your money", "hot deal",
    "act now", "get rich", "no risk", "instant cash", "hurry", "fast money", "big win",
    "money back", "free trial", "special offer", "act fast", "cashback", "sweepstakes",
    "new subscriber", "free membership", "no cost", "trial offer", "discount coupon",
    "cheap deal", "exclusive offer", "free bonus", "instant win", "fortune", "win big",
    "earn money", "prize draw", "free gift", "limited time offer", "flash sale", "deal of the day",
    "budget offer", "save now", "discounted price", "clearance sale", "bargain deal", "exclusive discount",
    "promo code", "instant discount", "price drop", "coupon code", "special discount", "members only",
    "save big", "extra savings", "daily deal", "limited edition", "free shipping", "best price",
    "doorbuster", "clearance offer", "price slash", "lowest price", "deal alert", "limited stock",
    "discount event", "reward giveaway", "VIP offer", "social media contest", "flash giveaway",
    "insider deal", "exclusive access", "member special", "coupon frenzy", "steal deal",
    "price clearance", "limited release", "offer ends soon", "last chance deal", "special savings",
    "hot offer", "mega sale", "daily discount", "online deal", "festival sale", "clearance markdown",
    "big discount", "bonus offer", "voucher", "promo blast", "promo event", "deal bonanza", "offer frenzy",
    "savings event", "discount extravaganza", "price bust", "bargain alert", "coupon mania",
    "offer marathon", "exclusive discount code", "instant rebate", "limited coupon", "bonus savings",
    "reward event", "in-store special", "digital coupon", "deal hotspot", "offer party", "sale alert",
    "promo frenzy", "cash incentive", "deal delight", "savings carnival", "price plunge", "special rate",
    "clearance blitz", "offer radar", "deal magnet", "discount radar", "price bomb", "savings splash",
    "offer splash", "deal dive", "discount dive", "coupon drop", "reward drop", "deal drop"}

def extract_keywords(text):
    """
    Extracts important words from a given message using Named Entity Recognition (NER) and a frequency-based approach.
    """
    if not text or text.strip() == "":
        return []

    text = re.sub(r'[^a-z\s]', '', text.lower())
    words = [lemmatizer.lemmatize(word) for word in text.split() if word not in stop_words and len(word) > 2]

    if len(words) < 2:
        return []

    doc = nlp(" ".join(words))
    ner_keywords = {ent.text.lower() for ent in doc.ents}

    vectorizer = CountVectorizer(max_features=10, stop_words="english")
    word_counts = vectorizer.fit_transform([" ".join(words)])
    frequent_words = set(vectorizer.get_feature_names_out())

    final_keywords = ner_keywords | frequent_words

    return list(final_keywords) if len(final_keywords) > 1 else []

def compute_fp_growth_score_alternative(extracted_keywords):
    """
    Computes a phishing score by checking how many extracted words match predefined phishing terms.
    Now includes **weighted** scoring for High, Medium, and Low-risk words.
    """
    if not extracted_keywords:
        return 0  # No phishing risk

    score = 0
    for keyword in extracted_keywords:
        if keyword in HIGH_RISK_KEYWORDS:
            score += 20  # High-risk words have more impact
        elif keyword in MEDIUM_RISK_KEYWORDS:
            score += 15  # Medium-risk words have moderate impact
        elif keyword in LOW_RISK_KEYWORDS:
            score += 10   # Low-risk words have minimal impact

    return min(100, score)


def process_message(message_type, original_text=None, email_subject=None, email_body=None):
    """
    Processes an input message, extracts keywords, computes a phishing score, and classifies it.
    """
    if message_type not in ["sms", "email"]:
        raise ValueError("Invalid message_type. Use 'sms' or 'email'.")

    text = original_text if message_type == "sms" else f"{email_subject or ''} {email_body or ''}"
    
    extracted_keywords = extract_keywords(text)

    score = compute_fp_growth_score_alternative(extracted_keywords)

    #Determine classification based on score
    if score >= 80:
        final_result = "high risk phishing"
    elif score >= 30:
        final_result = "medium risk phishing"
    elif score < 30:
        final_result = "legit"

    return {
        "extracted_keywords": extracted_keywords,
        "final_score": score,
        "final_result": final_result
    }
