# Simple test script to check if PDF API endpoint is working
import requests
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_simple_pdf():
    """Create a simple test PDF in memory"""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.drawString(100, 750, "Hello World - Test PDF")
    p.drawString(100, 720, "This is a test PDF for VirusTotal analysis")
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer.getvalue()

def test_pdf_api():
    """Test the PDF analysis API endpoint"""
    try:
        # Create test PDF
        pdf_data = create_simple_pdf()
        print(f"Created test PDF ({len(pdf_data)} bytes)")
        
        # Test API endpoint
        url = "http://127.0.0.1:5000/api/analyze_pdf"
        files = {'file': ('test.pdf', pdf_data, 'application/pdf')}
        
        print("Testing PDF analysis API...")
        response = requests.post(url, files=files)
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response content: {response.text[:500]}...")
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✅ API call successful!")
                print(f"Analysis result: {result.get('analysis', {}).get('classification', 'N/A')}")
                return True
            else:
                print(f"❌ API returned error: {result.get('error')}")
                return False
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_pdf_api()