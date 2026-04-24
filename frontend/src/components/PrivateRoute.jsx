import React, { useState, useEffect } from "react";
import { Navigate } from "react-router-dom";

const PrivateRoute = ({ role, children }) => {
  const [isChecking, setIsChecking] = useState(true);
  const [isValid, setIsValid] = useState(false);
  const [userRole, setUserRole] = useState(null);

  useEffect(() => {
    try {
      const parsed = JSON.parse(localStorage.getItem("currentUser") || "null");
      const currentUser = parsed && typeof parsed === "object" ? parsed : null;

      if (!currentUser || !currentUser.id) {
        setIsValid(false);
        setIsChecking(false);
        return;
      }

      setUserRole(currentUser.role || null);
      setIsValid(true);
      setIsChecking(false);
    } catch {
      setIsValid(false);
      setIsChecking(false);
    }
  }, []);

  if (isChecking) {
    return (
      <div
        style={{
          height: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "18px",
          color: "var(--muted-foreground)",
        }}
      >
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
