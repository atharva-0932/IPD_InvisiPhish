# pdf_analysis.py - VirusTotal PDF Analysis Integration
import requests
import time
import os
import hashlib
from typing import Dict, Any, Optional

def get_virustotal_api_key():
    """Get VirusTotal API key from environment variables"""
    return os.getenv('VIRUSTOTAL_API_KEY')

def analyze_pdf_with_virustotal(file_data: bytes, filename: str) -> Dict[str, Any]:
    """
    Analyze a PDF file using VirusTotal API
    Based on the existing sandboxVT.py implementation
    
    Args:
        file_data: The PDF file content as bytes
        filename: Name of the file
        
    Returns:
        Dictionary containing analysis results
    """
    api_key = get_virustotal_api_key()
    if not api_key:
        return {
            "success": False,
            "error": "VirusTotal API key not configured"
        }
    
    try:
        # Step 1: Upload file to VirusTotal (based on sandboxVT.py logic)
        url = "https://www.virustotal.com/api/v3/files"
        headers = {"x-apikey": api_key}
        
        print("[*] Uploading file to VirusTotal...")
        files = {"file": (filename, file_data, "application/pdf")}
        response = requests.post(url, headers=headers, files=files)
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Upload failed: {response.status_code} - {response.text}"
            }
        
        response_json = response.json()
        analysis_id = response_json.get("data", {}).get("id")
        
        if not analysis_id:
            return {
                "success": False,
                "error": "Failed to get analysis ID from VirusTotal"
            }
        
        print(f"[*] File submitted. Analysis ID: {analysis_id}")
        
        # Step 2: Wait for analysis to complete (based on sandboxVT.py logic)
        return wait_for_analysis_completion(analysis_id, filename, api_key)
        
    except requests.RequestException as e:
        return {
            "success": False,
            "error": f"Network error: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Analysis error: {str(e)}"
        }

def wait_for_analysis_completion(analysis_id: str, filename: str, api_key: str) -> Dict[str, Any]:
    """
    Wait for VirusTotal analysis to complete and return results
    Based on the existing sandboxVT.py polling logic
    """
    print("[*] Waiting for analysis to complete...")
    result_url = f"https://www.virustotal.com/api/v3/analyses/{analysis_id}"
    headers = {"x-apikey": api_key}
    
    # Use the same timing as sandboxVT.py
    MAX_WAIT_TIME = 150  # 2.5 minutes
    POLL_INTERVAL = 10   # Check every 10 seconds
    elapsed_time = 0
    
    while elapsed_time < MAX_WAIT_TIME:
        time.sleep(POLL_INTERVAL)
        elapsed_time += POLL_INTERVAL
        
        try:
            result_response = requests.get(result_url, headers=headers)
            result_data = result_response.json()
            status = result_data.get("data", {}).get("attributes", {}).get("status")
            
            print(f"[*] Status: {status} (Waited {elapsed_time}s)")
            
            if status == "completed":
                print("[+] Analysis Complete!")
                return parse_completed_analysis(result_data, filename, analysis_id)
            
            elif status in ["failed", "error"]:
                return {
                    "success": False,
                    "error": "VirusTotal analysis failed"
                }
                
        except Exception as e:
            print(f"[!] Error during polling: {str(e)}")
            continue  # Keep trying until timeout
    
    return {
        "success": False,
        "error": "Analysis timeout - VirusTotal took too long to process the file"
    }

def parse_completed_analysis(result_data: Dict[str, Any], filename: str, analysis_id: str) -> Dict[str, Any]:
    """
    Parse the completed VirusTotal analysis results
    Based on the existing sandboxVT.py output format
    """
    try:
        attributes = result_data.get("data", {}).get("attributes", {})
        stats = attributes.get("stats", {})
        
        # Extract the same stats as sandboxVT.py
        harmless = stats.get("harmless", 0)
        malicious = stats.get("malicious", 0)
        suspicious = stats.get("suspicious", 0)
        undetected = stats.get("undetected", 0)
        
        total_engines = harmless + malicious + suspicious + undetected
        
        # Calculate risk score (0-100 scale)
        if total_engines > 0:
            risk_score = round(((malicious * 100) + (suspicious * 60)) / total_engines, 1)
        else:
            risk_score = 0
        
        # Determine classification and risk level
        if malicious > 0:
            classification = "malicious"
            risk_level = "High Risk"
            result_type = "phishing"  # For frontend compatibility
        elif suspicious > 0:
            classification = "suspicious"
            risk_level = "Medium Risk"
            result_type = "suspicious"
        else:
            classification = "clean"
            risk_level = "Low Risk"
            result_type = "legitimate"
        
        # Generate threat details
        threat_details = []
        if malicious > 0:
            threat_details.append(f"Detected as malicious by {malicious} security engines")
        if suspicious > 0:
            threat_details.append(f"Flagged as suspicious by {suspicious} security engines")
        if harmless > 0:
            threat_details.append(f"Considered harmless by {harmless} security engines")
        if undetected > 0:
            threat_details.append(f"Undetected by {undetected} security engines")
        
        # Generate analysis summary
        if malicious > 0:
            analysis_summary = f"This PDF document has been identified as malicious by {malicious} out of {total_engines} security engines. It may contain harmful content such as embedded malware, suspicious scripts, or phishing elements."
        elif suspicious > 0:
            analysis_summary = f"This PDF document shows suspicious characteristics according to {suspicious} out of {total_engines} security engines. Exercise caution when opening this file."
        else:
            analysis_summary = f"This PDF document appears to be clean based on analysis by {total_engines} security engines. No immediate threats were detected."
        
        # Calculate confidence based on total engines that provided results
        confidence = min(95, max(60, int((total_engines / 70) * 100))) if total_engines > 0 else 50
        
        # Generate recommendations
        recommendations = generate_recommendations(classification, malicious, suspicious)
        
        return {
            "success": True,
            "analysis_id": analysis_id,
            "filename": filename,
            "analysis": {
                "score": min(10, max(1, int(risk_score / 10))) if risk_score > 0 else 1,  # 1-10 scale for frontend
                "result": result_type,
                "confidence": confidence,
                "threats": threat_details,
                "analysis": analysis_summary,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "classification": classification,
                "detection_stats": {
                    "harmless": harmless,
                    "malicious": malicious,
                    "suspicious": suspicious,
                    "undetected": undetected,
                    "total_engines": total_engines
                },
                "virustotal_details": {
                    "scan_date": attributes.get("date", int(time.time())),
                    "analysis_id": analysis_id
                }
            },
            "recommendations": recommendations
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to parse analysis results: {str(e)}"
        }

def generate_recommendations(classification: str, malicious_count: int, suspicious_count: int) -> list:
    """Generate security recommendations based on analysis results"""
    
    recommendations = []
    
    if classification == "malicious":
        recommendations.extend([
            "🚨 CRITICAL: This PDF is detected as MALICIOUS",
            "🛑 DO NOT open this file",
            "🗑️ Delete this file immediately",
            "🔒 Run a full system scan if you've already opened it",
            "📧 Report this file to your security team"
        ])
    elif classification == "suspicious":
        recommendations.extend([
            "⚠️ WARNING: This PDF shows suspicious characteristics", 
            "🔍 Exercise extreme caution before opening",
            "🏢 Verify the source through official channels",
            "💻 Consider opening in a sandboxed environment only",
            "📞 Contact sender to confirm they sent this file"
        ])
    else:  # clean
        recommendations.extend([
            "✅ File appears clean based on current analysis",
            "👀 Still verify the source if unexpected",
            "🛡️ Keep your PDF reader updated",
            "🔍 Be cautious of any unexpected behavior"
        ])
    
    return recommendations

def get_file_info(file_data: bytes, filename: str) -> Dict[str, Any]:
    """Get basic file information"""
    return {
        "filename": filename,
        "size": len(file_data),
        "size_mb": round(len(file_data) / (1024 * 1024), 2),
        "type": "PDF Document",
        "sha256": hashlib.sha256(file_data).hexdigest()
    }