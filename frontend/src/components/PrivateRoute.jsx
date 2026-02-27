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
        // JWT payload is the middle part between dots
        try {
          const payload = JSON.parse(
            atob(token.split(".")[1])
          );
          const now = Math.floor(Date.now() / 1000);
          if (payload.exp && payload.exp < now) {
            // token expired — clear storage
            localStorage.removeItem("authToken");
            localStorage.removeItem("currentUser");
            setIsValid(false);
            setIsChecking(false);
            return;
          }
        } catch {
          // if we cant decode token, reject it
          localStorage.removeItem("authToken");
          localStorage.removeItem("currentUser");
          setIsValid(false);
          setIsChecking(false);
          return;
        }

        setUserRole(currentUser.role);
        setIsValid(true);
        setIsChecking(false);

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

  if (role && userRole !== role) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

export default PrivateRoute;
