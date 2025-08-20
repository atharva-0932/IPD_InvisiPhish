import { Link, useLocation, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Shield, BarChart3, MessageSquare, Mail, FileText, History, Settings, LogOut } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { useToast } from "@/hooks/use-toast";

export const Navigation = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleLogout = async () => {
    const { error } = await supabase.auth.signOut();
    if (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to sign out"
      });
    } else {
      navigate("/auth");
    }
  };

  const navItems = [
    { path: "/", icon: BarChart3, label: "Dashboard" },
    { path: "/analyze/sms", icon: MessageSquare, label: "SMS Analysis" },
    { path: "/analyze/email", icon: Mail, label: "Email Analysis" },
    { path: "/analyze/pdf", icon: FileText, label: "PDF Analysis" },
    { path: "/history", icon: History, label: "History" },
    { path: "/settings", icon: Settings, label: "Settings" },
  ];

  return (
    <nav className="border-b bg-card">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Shield className="h-6 w-6 text-primary" />
              <span className="font-semibold text-lg">InvisiPhish</span>
            </div>
            <div className="hidden md:flex space-x-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <Link key={item.path} to={item.path}>
                    <Button 
                      variant={location.pathname === item.path ? "default" : "ghost"}
                      size="sm"
                      className="flex items-center space-x-2"
                    >
                      <Icon className="h-4 w-4" />
                      <span>{item.label}</span>
                    </Button>
                  </Link>
                );
              })}
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={handleLogout}>
            <LogOut className="h-4 w-4 mr-2" />
            Sign Out
          </Button>
        </div>
      </div>
    </nav>
  );
};