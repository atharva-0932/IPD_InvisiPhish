# InvisiPhish Guard

InvisiPhish Guard is a full-stack web application designed to protect users from phishing attacks by analyzing SMS and email messages. It leverages a multi-layered approach, combining traditional methods with modern AI to provide a comprehensive risk score and detailed analysis, helping users identify and avoid malicious content.

## ✨ Features

- **Multi-Channel Analysis**: Analyze both SMS messages and emails for potential phishing threats.
- **Advanced Scoring System**: A weighted scoring model that combines results from four distinct analysis layers:
    - **FP-Growth Analysis (15%)**: Identifies frequent patterns and suspicious keywords.
    - **Deep Learning (15%)**: Uses a DistilBERT model to classify text and detect phishing characteristics.
    - **Sentiment & Intent Analysis (30%)**: Employs a zero-shot classification model to understand the underlying intent (e.g., urgency, fear, authority).
    - **Generative AI (40%)**: Utilizes the Gemini Pro model for an in-depth, context-aware analysis, providing a final score and a human-readable explanation.
- **Detailed Results**: Get a final risk score (0-100), a clear classification ("Phishing" or "Legitimate"), and a breakdown of each analysis layer's findings.
- **Actionable Recommendations**: Receive clear, actionable advice based on the analysis result (e.g., "High Risk: Delete this message immediately").
- **Modern, Responsive UI**: A clean and intuitive user interface built with React, TypeScript, and Tailwind CSS, featuring a sleek lime and black theme with dark/light mode support.
- **Supabase Integration**: All analysis results are securely stored in a Supabase PostgreSQL database for tracking and future reference.


## 🛠️ Tech Stack

- **Frontend**:
    - **Framework**: React (with Vite)
    - **Language**: TypeScript
    - **Styling**: Tailwind CSS & shadcn/ui
    - **Routing**: React Router
- **Backend**:
    - **Framework**: Flask
    - **Language**: Python
    - **Deployment**: Vercel Serverless Functions
- **Database**:
    - Supabase (PostgreSQL)
- **AI & Machine Learning**:
    - Google Gemini Pro
    - Hugging Face Transformers (DistilBERT, BART)
    - Scikit-learn, NLTK, SpaCy






---

