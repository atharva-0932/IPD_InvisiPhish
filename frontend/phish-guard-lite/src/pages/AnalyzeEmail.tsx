import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, CheckCircle, Shield, Mail, ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";
import { useToast } from "@/hooks/use-toast";

export default function AnalyzeEmail() {
  const [senderEmail, setSenderEmail] = useState("");
  const [subject, setSubject] = useState("");
  const [emailContent, setEmailContent] = useState("");
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const handleAnalysis = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    
    // Mock analysis - replace with actual API call
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    const mockResult = {
      score: Math.floor(Math.random() * 10) + 1,
      result: Math.random() > 0.5 ? "phishing" : "legitimate",
      confidence: Math.floor(Math.random() * 30) + 70,
      threats: ["Suspicious domain", "Fake sender", "Malicious links", "Social engineering"],
      analysis: "This email exhibits characteristics commonly associated with phishing attempts, including deceptive sender information and suspicious links."
    };
    
    setAnalysisResult(mockResult);
    setLoading(false);
    
    toast({
      title: "Analysis Complete",
      description: `Email analyzed with ${mockResult.confidence}% confidence`
    });
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
          <h1 className="text-3xl font-bold">Email Analysis</h1>
          <p className="text-muted-foreground">Analyze email messages for phishing threats</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Mail className="h-5 w-5" />
              <span>Email Message Input</span>
            </CardTitle>
            <CardDescription>
              Enter the email message details for analysis
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAnalysis} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="sender-email">Sender Email</Label>
                <Input
                  id="sender-email"
                  type="email"
                  placeholder="sender@example.com"
                  value={senderEmail}
                  onChange={(e) => setSenderEmail(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="subject">Subject Line</Label>
                <Input
                  id="subject"
                  placeholder="Email subject..."
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email-content">Email Content</Label>
                <Textarea
                  id="email-content"
                  placeholder="Enter the email message content..."
                  className="min-h-[120px]"
                  value={emailContent}
                  onChange={(e) => setEmailContent(e.target.value)}
                  required
                />
              </div>
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Analyzing..." : "Analyze Email"}
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
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}