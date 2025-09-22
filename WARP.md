# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Code Architecture

This project is a phishing detection service built with Flask. It analyzes SMS and email messages to determine if they are legitimate or phishing attempts. The core logic is distributed across several key modules:

- **`main.py`**: The entry point of the Flask application. It creates and runs the Flask app.

- **`__init__.py`**: Initializes the Flask application, enables CORS, and registers the API routes.

- **`routes.py`**: Defines the API endpoints for storing and retrieving messages. It orchestrates the analysis pipeline by calling other modules.

- **`database.py`**: Manages the connection to the Supabase database. It includes functions to store and retrieve messages, as well as to analyze sender details.

- **`preprocess.py`**: Contains functions for cleaning and preprocessing text data from messages. It extracts links and cleans the message body and subject.

- **`fpgrowth.py`**: Implements the FP-Growth algorithm to identify frequent patterns and keywords in messages. It assigns a phishing score based on predefined risk keywords.

- **`deeplearning.py`**: Uses a pre-trained DistilBERT model to perform sequence classification and calculate a phishing score.

- **`sentiment.py`**: a zero-shot classification model to analyze the intent of the message (e.g., urgency, fear, reward).

- **`genai.py`**: Leverages a generative AI model to provide an additional layer of analysis and generate a phishing score and explanation.

- **`.env`**: Stores environment variables, including API keys for Supabase and the generative AI model.

The application follows a modular architecture where each component is responsible for a specific part of the analysis. The final phishing score is a weighted average of the scores from the FP-Growth, deep learning, sentiment analysis, and generative AI models.

## Common Commands

- **Run the application**:

  To run the application, you need to start both the backend and the frontend servers.

  - **Backend**:
    ```bash
    python main.py
    ```

  - **Frontend**:
    ```bash
    cd frontend/phish-guard-lite
    npm install
    npm run dev
    ```

- **Install dependencies**:
  There is no `requirements.txt` file, but you can generate one using `pip freeze > requirements.txt`. Then, you can install the dependencies using:
  ```bash
  pip install -r requirements.txt
  ```

- **Run tests**:
  There are no tests in the project. You can create a `tests` directory and add unit tests for the different modules.
