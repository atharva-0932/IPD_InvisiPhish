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
    setAnalysisResult(null);

    try {
      const response = await fetch('http://127.0.0.1:5000/analyze_message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message_type: 'email',
          sender_email: senderEmail,
          email_subject: subject,
          email_body: emailContent,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      setAnalysisResult(result.analysis);

      toast({
        title: "Analysis Complete",
        description: `Email analyzed successfully.`,
      });

    } catch (error) {
      console.error("Analysis failed:", error);
      toast({
        title: "Analysis Failed",
        description: "Could not analyze the email. Please try again.",
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
                <Badge variant={analysisResult.final_score > 70 ? "destructive" : analysisResult.final_score > 40 ? "secondary" : "default"}>
                  {analysisResult.final_score}/100
                </Badge>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="font-medium">Classification:</span>
                <Badge variant={getResultVariant(analysisResult.final_result.toLowerCase())} className="flex items-center space-x-1">
                  {getResultIcon(analysisResult.final_result.toLowerCase())}
                  <span className="capitalize">{analysisResult.final_result}</span>
                </Badge>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="font-medium">Risk Level:</span>
                <span className="text-sm">{analysisResult.risk_level}</span>
              </div>
              
              {analysisResult.scores_breakdown.genai.explanation && (
                <div>
                  <span className="font-medium block mb-2">GenAI Feedback:</span>
                  <p className="text-sm text-muted-foreground">{analysisResult.scores_breakdown.genai.explanation}</p>
                </div>
              )}

              {analysisResult.scores_breakdown.fp_growth.keywords && analysisResult.scores_breakdown.fp_growth.keywords.length > 0 && (
                <div>
                  <span className="font-medium block mb-2">Extracted Keywords:</span>
                  <div className="flex flex-wrap gap-2">
                    {analysisResult.scores_breakdown.fp_growth.keywords.map((keyword: string, index: number) => (
                      <Badge key={index} variant="secondary">{keyword}</Badge>
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