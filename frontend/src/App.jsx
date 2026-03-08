import { useState, useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import Register from "./pages/Register";
import Login from "./pages/Login";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import SplashScreen from "./pages/SplashScreen";
import SponsorDashboard from "./pages/SponsorDashboard";
import OrganizerDashboard from "./pages/OrganizerDashboard";
import InfluencerDashboard from "./pages/InfluencerDashboard";
import PublicProfile from "./pages/PublicProfile";
import AnalyticsPage from "./pages/AnalyticsPage";
import LandingPage from "./pages/LandingPage";
import PrivateRoute from "./components/PrivateRoute";

function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem("app-theme") || "dark");

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem("app-theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    if (!document.startViewTransition) {
      setTheme(prev => prev === 'dark' ? 'light' : 'dark');
      return;
    }
    
    document.startViewTransition(() => {
      setTheme(prev => prev === 'dark' ? 'light' : 'dark');
    });
  };

  return (
    <>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/profile/:userId" element={<PublicProfile />} />
        <Route
          path="/analytics/:userId?"
          element={(
            <PrivateRoute>
              <AnalyticsPage />
            </PrivateRoute>
          )}
        />
        <Route
          path="/sponsor-dashboard"
          element={(
            <PrivateRoute role="sponsor">
              <SponsorDashboard />
            </PrivateRoute>
          )}
        />
        <Route
          path="/organizer-dashboard"
          element={(
            <PrivateRoute role="organizer">
              <OrganizerDashboard />
            </PrivateRoute>
          )}
        />
        <Route
          path="/influencer-dashboard"
          element={(
            <PrivateRoute role="influencer">
              <InfluencerDashboard />
            </PrivateRoute>
          )}
        />
      </Routes>
    </>
  );
}

export default App;

