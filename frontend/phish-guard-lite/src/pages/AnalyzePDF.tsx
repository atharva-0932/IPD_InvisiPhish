import { useState, useRef } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, CheckCircle, Shield, FileText, Upload, ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";
import { useToast } from "@/hooks/use-toast";

export default function AnalyzePDF() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.type === "application/pdf") {
        setSelectedFile(file);
        toast({
          title: "File Selected",
          description: `${file.name} ready for analysis`
        });
      } else {
        toast({
          variant: "destructive",
          title: "Invalid File Type",
          description: "Please select a PDF file"
        });
      }
    }
  };

  const handleAnalysis = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;
    
    setLoading(true);
    setAnalysisResult(null);

    try {
      console.log('🚀 Starting PDF analysis for:', selectedFile.name);
      
      // Create FormData to send the file
      const formData = new FormData();
      formData.append('file', selectedFile);
      console.log('📦 FormData created with file:', selectedFile.name);

      console.log('📡 Making API call to /api/analyze_pdf');
      const response = await fetch('/api/analyze_pdf', {
        method: 'POST',
        body: formData,
      });
      console.log('📡 Response received:', response.status, response.statusText);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('📋 API Response data:', result);
      
      if (!result.success) {
        console.error('❌ API returned error:', result.error);
        throw new Error(result.error || 'Analysis failed');
      }

      console.log('✅ Analysis successful, mapping results...');
      // Map the backend response to the frontend expected format
      const mappedResult = {
        score: result.analysis.score,
        result: result.analysis.result,
        confidence: result.analysis.confidence,
        threats: result.analysis.threats || [],
        analysis: result.analysis.analysis,
        fileName: result.fileName,
        fileSize: result.fileSize,
        // Additional VirusTotal specific data
        riskScore: result.analysis.risk_score,
        riskLevel: result.analysis.risk_level,
        classification: result.analysis.classification,
        detectionStats: result.analysis.detection_stats,
        recommendations: result.recommendations
      };
      
      console.log('🎯 Final mapped result:', mappedResult);
      setAnalysisResult(mappedResult);

      toast({
        title: "Analysis Complete",
        description: `PDF analyzed with ${mappedResult.confidence}% confidence using VirusTotal`
      });

    } catch (error) {
      console.error("PDF Analysis failed:", error);
      toast({
        title: "Analysis Failed",
        description: error instanceof Error ? error.message : "Could not analyze the PDF. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const getResultVariant = (result: string) => {
    switch (result) {
      case "phishing":
        return "destructive";
      case "legitimate":
        return "default";
      default:
        return "secondary";
    }
  };

  const getResultIcon = (result: string) => {
    switch (result) {
      case "phishing":
        return <AlertTriangle className="h-4 w-4" />;
      case "legitimate":
        return <CheckCircle className="h-4 w-4" />;
      default:
        return <Shield className="h-4 w-4" />;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-4">
        <Link to="/">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold">PDF Analysis</h1>
          <p className="text-muted-foreground">Analyze PDF documents for phishing threats</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <FileText className="h-5 w-5" />
              <span>PDF Document Upload</span>
            </CardTitle>
            <CardDescription>
              Upload a PDF document for phishing analysis
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAnalysis} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="pdf-file">Select PDF File</Label>
                <div className="flex items-center space-x-2">
                  <Input
                    ref={fileInputRef}
                    id="pdf-file"
                    type="file"
                    accept=".pdf"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    className="flex-1"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <Upload className="h-4 w-4 mr-2" />
                    {selectedFile ? selectedFile.name : "Choose PDF File"}
                  </Button>
                </div>
                {selectedFile && (
                  <div className="text-sm text-muted-foreground">
                    File size: {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </div>
                )}
              </div>
              <Button type="submit" className="w-full" disabled={loading || !selectedFile}>
                {loading ? "Analyzing..." : "Analyze PDF"}
              </Button>
            </form>
          </CardContent>
        </Card>

        {analysisResult && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Shield className="h-5 w-5" />
                <span>Analysis Results</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="font-medium">File Name:</span>
                <span className="text-sm text-muted-foreground truncate max-w-[200px]">
                  {analysisResult.fileName}
                </span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="font-medium">File Size:</span>
                <span className="text-sm">{analysisResult.fileSize}</span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="font-medium">Risk Score:</span>
                <Badge variant={analysisResult.score > 7 ? "destructive" : analysisResult.score > 4 ? "secondary" : "default"}>
                  {analysisResult.score}/10
                </Badge>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="font-medium">Classification:</span>
                <Badge variant={getResultVariant(analysisResult.result)} className="flex items-center space-x-1">
                  {getResultIcon(analysisResult.result)}
                  <span className="capitalize">{analysisResult.result}</span>
                </Badge>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="font-medium">Confidence:</span>
                <span className="text-sm">{analysisResult.confidence}%</span>
              </div>
              
              {analysisResult.threats && (
                <div>
                  <span className="font-medium block mb-2">Detected Threats:</span>
                  <div className="space-y-1">
                    {analysisResult.threats.map((threat: string, index: number) => (
                      <Badge key={index} variant="outline" className="mr-2 mb-1">
                        {threat}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              
              <div>
                <span className="font-medium block mb-2">Analysis Summary:</span>
                <p className="text-sm text-muted-foreground">{analysisResult.analysis}</p>
              </div>

              {analysisResult.detectionStats && (
                <div>
                  <span className="font-medium block mb-2">VirusTotal Detection Stats:</span>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>Malicious: <Badge variant="destructive">{analysisResult.detectionStats.malicious}</Badge></div>
                    <div>Suspicious: <Badge variant="secondary">{analysisResult.detectionStats.suspicious}</Badge></div>
                    <div>Harmless: <Badge variant="default">{analysisResult.detectionStats.harmless}</Badge></div>
                    <div>Undetected: <Badge variant="outline">{analysisResult.detectionStats.undetected}</Badge></div>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    Scanned by {analysisResult.detectionStats.total_engines} security engines
                  </p>
                </div>
              )}

              {analysisResult.recommendations && (
                <div>
                  <span className="font-medium block mb-2">Security Recommendations:</span>
                  <div className="space-y-1">
                    {analysisResult.recommendations.slice(0, 5).map((rec: string, index: number) => (
                      <p key={index} className="text-xs text-muted-foreground flex items-start">
                        <span className="mr-2">•</span>
                        <span>{rec}</span>
                      </p>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}