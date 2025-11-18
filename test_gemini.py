import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

def test_gemini_api():
    """Test if Gemini API is working correctly"""
    
    # Check if API key exists
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY not found in .env file")
        return False
    
    print(f"✓ API Key found: {api_key[:10]}...{api_key[-4:]}")
    
    try:
        # Initialize client
        print("\n[1/3] Initializing Gemini client...")
        client = genai.Client(api_key=api_key)
        print("✓ Client initialized successfully")
        
        # Test with a simple message
        print("\n[2/3] Testing API with a sample message...")
        test_message = "Congratulations! You've won $1000. Click here to claim: http://fake-site.com"
        
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=test_message)],
            ),
        ]
        
        config = types.GenerateContentConfig(
            temperature=0.6,
            response_mime_type="application/json",
            system_instruction=[
                types.Part.from_text(text="""
                Analyze this message for phishing. Return JSON with:
                - "phishing_score" (0-100)
                - "explanation" (brief text)
                """),
            ],
        )
        
        response_text = ""
        for chunk in client.models.generate_content_stream(
            model="gemini-2.0-flash",
            contents=contents,
            config=config,
        ):
            if chunk.text:
                response_text += chunk.text
        
        print("✓ API response received")
        
        # Parse response
        print("\n[3/3] Parsing response...")
        import json
        result = json.loads(response_text)
        
        print("\n✅ SUCCESS! Gemini API is working perfectly!")
        print(f"\nSample Response:")
        print(f"  Phishing Score: {result.get('phishing_score', 'N/A')}")
        print(f"  Explanation: {result.get('explanation', 'N/A')[:100]}...")
        
        return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ ERROR: {error_msg}")
        
        # Provide specific guidance
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            print("\n🔍 Issue: Rate Limit Exceeded")
            print("   Solutions:")
            print("   1. Wait a few minutes and try again")
            print("   2. Check your quota at: https://aistudio.google.com/app/apikey")
            print("   3. Your free tier may have limits (15 requests/minute, 1500/day)")
            
        elif "401" in error_msg or "403" in error_msg or "API_KEY_INVALID" in error_msg:
            print("\n🔍 Issue: Invalid API Key")
            print("   Solutions:")
            print("   1. Verify your API key at: https://aistudio.google.com/app/apikey")
            print("   2. Generate a new API key if needed")
            print("   3. Make sure there are no extra spaces in your .env file")
            
        elif "model not found" in error_msg.lower():
            print("\n🔍 Issue: Model Not Available")
            print("   Solutions:")
            print("   1. Check if 'gemini-2.0-flash' is available in your region")
            print("   2. Try using 'gemini-1.5-flash' instead")
            
        else:
            print("\n🔍 Generic API Error")
            print("   Check:")
            print("   1. Internet connection")
            print("   2. Firewall/proxy settings")
            print("   3. Google AI Studio status: https://status.cloud.google.com/")
        
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("GEMINI API CONFIGURATION TEST")
    print("=" * 60)
    
    success = test_gemini_api()
    
    print("\n" + "=" * 60)
    if success:
        print("Result: Your Gemini API is configured correctly! ✅")
    else:
        print("Result: Please fix the issues above ❌")
    print("=" * 60)
