import React, { useEffect, useMemo, useState } from "react";
import "./ChatBox.css";

const ChatBox = ({ role, title = "Live Chat", onClose, chatKey }) => {
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [ws, setWs] = useState(null);

  const messagesEndRef = React.useRef(null);
  const containerRef = React.useRef(null);
  const [isAtBottom, setIsAtBottom] = useState(true);

  // Parse dealId from chatKey (format: deal_12)
  const dealId = useMemo(() => chatKey.split("_")[1], [chatKey]);

  // Current user info
  const currentUser = useMemo(() => {
    try { return JSON.parse(localStorage.getItem("currentUser") || "{}"); } catch { return {}; }
  }, []);

  const myId = Number(currentUser.id);

  // Load history and setup WebSocket
  useEffect(() => {
    if (!dealId) return;

    const apiBase = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
    const wsHost = apiBase.replace(/^http/, "ws");

    // 1. Fetch history
    const fetchHistory = async () => {
      try {
        const token = localStorage.getItem("authToken");
        const response = await fetch(`${apiBase}/chat/history/${dealId}`, {
          headers: { "Authorization": `Bearer ${token}` }
        });
        const data = await response.json();
        setMessages(data.map(m => ({
          sender_id: m.sender_id,
          sender_role: m.sender_role,
          sender_name: m.sender_name || m.sender_role,
          text: m.content,
          id: m.id,
          timestamp: m.timestamp
        })));
      } catch (err) {
        console.error("Failed to fetch chat history:", err);
      }
    };

    fetchHistory();

    // 2. Setup WebSocket
    const token = localStorage.getItem("authToken");
    const socket = new WebSocket(`${wsHost}/chat/ws/${dealId}?token=${token}`);

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMessages(prev => {
        if (prev.find(m => m.id === data.id)) return prev;
        return [...prev, {
          sender_id: data.sender_id,
          sender_role: data.sender_role,
          sender_name: data.sender_name || data.sender_role,
          text: data.text,
          id: data.id,
          timestamp: data.timestamp
        }];
      });
    };

    socket.onclose = () => console.log("Chat WebSocket closed");
    socket.onerror = (err) => console.error("Chat WebSocket error:", err);

    setWs(socket);

    return () => {
      socket.close();
    };
  }, [dealId]);

  // scroll behaviour on new messages
  useEffect(() => {
    if (isAtBottom && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isAtBottom]);

  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const bottom = scrollTop + clientHeight >= scrollHeight - 10;
    setIsAtBottom(bottom);
  };

  const handleSend = () => {
    if (!input.trim() || !ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ text: input }));
    setInput("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const formatTime = (ts) => {
    if (!ts) return "";
    try {
      return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    } catch {
      return "";
    }
  };

  // Own = current user's messages. Use sender_id (most reliable), fallback to role.
  const isOwnMessage = (msg) => {
    const sid = Number(msg.sender_id);
    if (sid && myId) return sid === myId;
    return msg.sender_role === role;
  };

  if (isMinimized) {
    return (
      <div className="chat-minimized-bar" onClick={() => setIsMinimized(false)}>
        <div className="chat-minimized-info">
          <div className="chat-minimized-dot"></div>
          <span>{title}</span>
          {messages.length > 0 && <span className="chat-unread-pill">{messages.length}</span>}
        </div>
        <div className="chat-header-actions" onClick={e => e.stopPropagation()}>
          <button type="button" className="chat-control-btn" onClick={() => setIsMinimized(false)}>↑</button>
          {onClose && (
            <button type="button" className="chat-control-btn close" onClick={onClose}>✕</button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="chat-container">
      {/* Header */}
      <div className="chat-header">
        <div className="chat-header-info">
          <div className="chat-header-avatar">{title.charAt(title.lastIndexOf(" ") + 1)}</div>
          <div>
            <div className="chat-header-title">{title}</div>
            <div className="chat-header-status">
              <span className="chat-online-dot"></span> Deal Chat
            </div>
          </div>
        </div>
        <div className="chat-header-actions">
          <button type="button" className="chat-control-btn" onClick={() => setIsMinimized(true)} aria-label="Minimize">_</button>
          {onClose && (
            <button type="button" className="chat-control-btn close" onClick={onClose} aria-label="Close">✕</button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="chat-messages" ref={containerRef} onScroll={handleScroll}>
        {messages.length === 0 && (
          <div className="chat-empty">
            <div className="chat-empty-icon">💬</div>
            <p>No messages yet. Say hello!</p>
          </div>
        )}
        {messages.map((msg, index) => {
          const mine = isOwnMessage(msg);
          // Show sender name only for first message in a consecutive group from 'other'
          const prevMsg = messages[index - 1];
          const showName = !mine && (
            !prevMsg || isOwnMessage(prevMsg) || prevMsg.sender_id !== msg.sender_id
          );
          return (
            <div key={msg.id || index} className={`chat-row ${mine ? "chat-row-own" : "chat-row-other"}`}>
              {/* Sender name label for other user's first consecutive message */}
              {!mine && showName && (
                <div className="chat-sender-name" style={{ color: msg.sender_role === 'organizer' ? '#10b981' : msg.sender_role === 'influencer' ? '#f59e0b' : '#818cf8' }}>
                  {msg.sender_name || msg.sender_role}
                </div>
              )}
              <div className={`chat-bubble ${mine ? "bubble-own" : "bubble-other"}`}>
                <div className="bubble-text">{msg.text}</div>
                <div className="bubble-time">
                  {formatTime(msg.timestamp)}
                  {mine && <span className="bubble-tick">✓✓</span>}
                </div>
              </div>
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="chat-input-area">
        <input
          type="text"
          placeholder="Type a message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button onClick={handleSend} disabled={!input.trim()}>Send</button>
      </div>
    </div>
  );
};

export default ChatBox;
