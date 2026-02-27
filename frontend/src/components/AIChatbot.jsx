import React, { useState } from 'react';
import './AIChatbot.css';

const AIChatbot = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="ai-chatbot-wrapper">
      {isOpen && (
        <div className="ai-tooltip glass-morphism">
          <div className="ai-tooltip-header">
            <span className="ai-badge">AI Assistant</span>
            <span className="ai-tooltip-title">HubBot</span>
          </div>
          <p className="ai-tooltip-desc">Your intelligent sponsorship companion.</p>
          <span className="coming-soon-label">🚀 Coming Soon</span>
        </div>
      )}
      <div 
        className="ai-chatbot-fab" 
        onMouseEnter={() => setIsOpen(true)}
        onMouseLeave={() => setIsOpen(false)}
        onClick={() => setIsOpen(!isOpen)}
      >
        <span>💬</span>
      </div>
    </div>
  );
};

export default AIChatbot;
