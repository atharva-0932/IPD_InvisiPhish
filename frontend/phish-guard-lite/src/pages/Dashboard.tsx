import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { BarChart3, Shield, AlertTriangle, CheckCircle, MessageSquare, Mail, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "react-router-dom";

// Mock data for now - will connect to API later
const mockStats = {
  totalMessages: 1247,
  phishingPercentage: 23,
  averageScore: 7.2,
  topIntent: "credential_harvesting"
};

const mockRecentMessages = [
  {
    id: 1,
    type: "sms",
    sender: "+1234567890",
    content: "Your account has been suspended. Click here to verify...",
    score: 9.2,
    result: "phishing",
    timestamp: "2024-01-15 14:30"
  },
  {
    id: 2,
    type: "email",
    sender: "support@bank.com",
    content: "Please update your payment information...",
    score: 3.4,
    result: "legitimate",
    timestamp: "2024-01-15 13:45"
  },
  {
    id: 3,
    type: "sms",
    sender: "+9876543210",
    content: "Congratulations! You've won $1000...",
    score: 8.7,
    result: "phishing",
    timestamp: "2024-01-15 12:15"
  }
];

export default function Dashboard() {
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
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <div className="flex space-x-2">
          <Link to="/analyze/sms">
            <Button>
              <MessageSquare className="h-4 w-4 mr-2" />
              Analyze SMS
            </Button>
          </Link>
          <Link to="/analyze/email">
            <Button variant="outline">
              <Mail className="h-4 w-4 mr-2" />
              Analyze Email
            </Button>
          </Link>
          <Link to="/analyze/pdf">
            <Button variant="outline">
              <FileText className="h-4 w-4 mr-2" />
              Analyze PDF
            </Button>
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Messages</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockStats.totalMessages.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              All analyzed messages
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Phishing Rate</CardTitle>
            <AlertTriangle className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockStats.phishingPercentage}%</div>
            <p className="text-xs text-muted-foreground">
              Messages flagged as phishing
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Average Score</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockStats.averageScore}/10</div>
            <p className="text-xs text-muted-foreground">
              Risk assessment score
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Top Intent</CardTitle>
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold capitalize">{mockStats.topIntent.replace('_', ' ')}</div>
            <p className="text-xs text-muted-foreground">
              Most common attack type
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Messages */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Analysis Results</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Type</TableHead>
                <TableHead>Sender</TableHead>
                <TableHead>Content Preview</TableHead>
                <TableHead>Score</TableHead>
                <TableHead>Result</TableHead>
                <TableHead>Time</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockRecentMessages.map((message) => (
                <TableRow key={message.id}>
                  <TableCell>
                    <Badge variant="outline">{message.type.toUpperCase()}</Badge>
                  </TableCell>
                  <TableCell className="font-medium">{message.sender}</TableCell>
                  <TableCell className="max-w-xs truncate">{message.content}</TableCell>
                  <TableCell>
                    <div className="flex items-center space-x-2">
                      <span className="font-medium">{message.score}</span>
                      <div className="w-20 bg-muted rounded-full h-2">
                        <div 
                          className="bg-primary h-2 rounded-full" 
                          style={{ width: `${message.score * 10}%` }}
                        />
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={getResultVariant(message.result)} className="flex items-center space-x-1 w-fit">
                      {getResultIcon(message.result)}
                      <span className="capitalize">{message.result}</span>
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{message.timestamp}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}