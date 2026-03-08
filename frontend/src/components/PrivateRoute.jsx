import React, { useState, useEffect } from "react";
import { Navigate } from "react-router-dom";

const PrivateRoute = ({ role, children }) => {
  const [isChecking, setIsChecking] = useState(true);
  const [isValid, setIsValid] = useState(false);
  const [userRole, setUserRole] = useState(null);

  useEffect(() => {
    const validate = () => {
      try {
        const token = localStorage.getItem("authToken");
        const parsed = JSON.parse(
          localStorage.getItem("currentUser") || "null"
        );
        const currentUser = 
          parsed && typeof parsed === "object" ? parsed : null;

        if (!token || !currentUser) {
          setIsValid(false);
          setIsChecking(false);
          return;
        }

        // check token expiry from JWT payload
        // JWT uses base64url (not standard base64) — must convert before atob()
        try {
          const base64url = token.split(".")[1];
          // base64url → base64: replace URL-safe chars and add padding
          const base64 = base64url
            .replace(/-/g, "+")
            .replace(/_/g, "/")
            .padEnd(base64url.length + ((4 - (base64url.length % 4)) % 4), "=");
          
          // Robust UTF-8 decoding for atob
          const payload = JSON.parse(decodeURIComponent(escape(atob(base64))));
          const now = Math.floor(Date.now() / 1000);
          
          if (payload.exp && payload.exp < now) {
            // token is provably expired — clear storage and redirect
            localStorage.removeItem("authToken");
            localStorage.removeItem("currentUser");
            setIsValid(false);
            setIsChecking(false);
            return;
          }
          
          // Token is valid (not expired)
          setUserRole(currentUser.role);
          setIsValid(true);
          setIsChecking(false);
        } catch {
          // Cannot decode token payload — we'll trust it anyway and let the
          // server reject it on a real API call if it's truly bad.
          // This avoids the login-redirect loop if the browser has trouble decoding.
          setUserRole(currentUser.role);
          setIsValid(true);
          setIsChecking(false);
        }
      } catch {
        setIsValid(false);
        setIsChecking(false);
      }
    };

    validate();
  }, []);

  // show nothing while checking to avoid flash
  if (isChecking) {
    return (
      <div style={{
        height: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: "18px",
        color: "#64748b"
      }}>
        Loading...
      </div>
    );
  }

  if (!isValid) {
    return <Navigate to="/login" replace />;
  }

  if (role && userRole?.toLowerCase() !== role?.toLowerCase()) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

export default PrivateRoute;
