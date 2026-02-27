import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./SplashScreen.css";

const SplashScreen = ({ onComplete }) => {
  const navigate = useNavigate();
  const [showLogo, setShowLogo] = useState(false);
  const [showText, setShowText] = useState(false);
  const [fadeOut, setFadeOut] = useState(false);

  useEffect(() => {
    // Stage 1: Reveal SS Logo
    setTimeout(() => setShowLogo(true), 500);
    
    // Stage 2: Reveal Text
    setTimeout(() => setShowText(true), 1200);
    
    // Stage 3: Initiate Fade out
    setTimeout(() => setFadeOut(true), 3200);
    
    // Stage 4: Finish
    setTimeout(() => {
      if (onComplete) {
        onComplete();
      } else {
        navigate("/login");
      }
    }, 4000);
  }, [navigate, onComplete]);

  return (
    <div className={`splash-screen ${fadeOut ? "fade-out" : ""}`}>
      <div className="splash-content">
        <div className={`splash-logo ${showLogo ? "reveal" : ""}`}>
          <div className="inner-logo">SS</div>
          <div className="logo-ring"></div>
        </div>
        <div className={`splash-text ${showText ? "reveal" : ""}`}>
          <h1 className="brand-name">
            <span className="light">SPONSOR</span>
            <span className="bold">HUB</span>
          </h1>
          <p className="tagline">Empowering Partnerships through Innovation</p>
          <div className="loader-line"></div>
        </div>
      </div>
      
      <div className="splash-bg">
        <div className="gradient-orb orb-1"></div>
        <div className="gradient-orb orb-2"></div>
      </div>
    </div>
  );
};

export default SplashScreen;
