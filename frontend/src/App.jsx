import { useState, useEffect, lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import PrivateRoute from "./components/PrivateRoute";

const Register = lazy(() => import("./pages/Register"));
const Login = lazy(() => import("./pages/Login"));
const ForgotPassword = lazy(() => import("./pages/ForgotPassword"));
const ResetPassword = lazy(() => import("./pages/ResetPassword"));
const VerifyEmail = lazy(() => import("./pages/VerifyEmail"));
const SponsorDashboard = lazy(() => import("./pages/SponsorDashboard"));
const OrganizerDashboard = lazy(() => import("./pages/OrganizerDashboard"));
const InfluencerDashboard = lazy(() => import("./pages/InfluencerDashboard"));
const PublicProfile = lazy(() => import("./pages/PublicProfile"));
const MyProfilePage = lazy(() => import("./pages/MyProfilePage"));
const AnalyticsPage = lazy(() => import("./pages/AnalyticsPage"));
const LandingPage = lazy(() => import("./pages/LandingPage"));
const ScaleOpsPage = lazy(() => import("./pages/ScaleOpsPage"));

const PageLoader = () => (
  <div
    style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "var(--muted)",
      fontSize: "0.95rem",
      letterSpacing: "0.02em",
    }}
  >
    Loading...
  </div>
);

function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem("app-theme") || "dark");

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem("app-theme", theme);
  }, [theme]);

  // Master Auth Verification - Ensures the local user still exists on the server
  useEffect(() => {
    const verifyAuth = async () => {
      const user = JSON.parse(localStorage.getItem("currentUser") || "null");
      
      if (user?.id) {
        try {
          // Attempt to fetch current user to verify session/account existence
          const { fetchUser } = await import("./services/api");
          await fetchUser(user.id);
        } catch (err) {
          // If fetch fails (401 or 404), api.js interceptor will handle cleanup/redirect
          console.error("Auth verification failed:", err);
        }
      }
    };
    verifyAuth();
  }, []);

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
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route path="/profile/:userId" element={<PublicProfile />} />
        <Route
          path="/my-profile"
          element={(
            <PrivateRoute>
              <MyProfilePage />
            </PrivateRoute>
          )}
        />
        <Route
          path="/analytics/:userId?"
          element={(
            <PrivateRoute>
              <AnalyticsPage />
            </PrivateRoute>
          )}
        />
        <Route
          path="/scale-ops"
          element={(
            <PrivateRoute>
              <ScaleOpsPage />
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
    </Suspense>
  );
}

export default App;
