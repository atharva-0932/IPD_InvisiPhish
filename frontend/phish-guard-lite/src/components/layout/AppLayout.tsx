import { Outlet } from "react-router-dom";
import { Navigation } from "./Navigation";

export const AppLayout = () => {
  return (
    <div className="min-h-screen bg-background">
      <Navigation />
      <main className="container mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
};