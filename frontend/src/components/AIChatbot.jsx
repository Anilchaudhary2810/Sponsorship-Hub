import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import {
  clearAIHistory,
  fetchAIContext,
  fetchAIHistory,
  fetchPublicAIContext,
  sendAIMessage,
  sendPublicAIMessage,
} from "../services/api";
import "./AIChatbot.css";

const QUICK_PROMPTS = [
  "What can I do on this page?",
  "Summarize my latest deal pipeline status",
  "What should I do next to close more deals?",
];

const readCurrentUser = () => {
  try {
    const parsed = JSON.parse(localStorage.getItem("currentUser") || "null");
    if (parsed && parsed.id) {
      return parsed;
    }
  } catch {
    // ignore malformed local storage
  }
  return null;
};

const sanitizeText = (value) => {
  if (typeof value !== "string") {
    return "";
  }
  return value
    .replace(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi, "[redacted-email]")
    .replace(/\+?\d[\d\s\-()]{7,}/g, "[redacted-phone]")
    .replace(/\s+/g, " ")
    .trim();
};

const uniqueTop = (items, limit = 8) => {
  const seen = new Set();
  const output = [];
  for (const raw of items) {
    const text = sanitizeText(raw);
    if (!text || seen.has(text)) {
      continue;
    }
    seen.add(text);
    output.push(text);
    if (output.length >= limit) {
      break;
    }
  }
  return output;
};

const collectPageDataSnapshot = (pathname) => {
  const headingTexts = uniqueTop(
    Array.from(document.querySelectorAll("h1, h2, h3")).map((node) => node.textContent || ""),
    10
  );

  const statCandidates = uniqueTop(
    Array.from(
      document.querySelectorAll(
        ".stat-card, .metric-card, [class*='stat'], [class*='metric'], [class*='kpi'], [class*='deal'], [class*='revenue'], [class*='pipeline']"
      )
    ).map((node) => node.textContent || ""),
    20
  ).filter((value) => /[\d₹$%]/.test(value));

  const pageRoot = document.querySelector("main") || document.body;
  const bodyText = sanitizeText(pageRoot?.innerText || "").slice(0, 720);

  return {
    path: pathname,
    title: document.title || "Sponsorship Hub",
    headings: headingTexts,
    stats_preview: statCandidates,
    page_text_preview: bodyText,
    captured_at: new Date().toISOString(),
  };
};

const mapHistory = (rows = []) =>
  rows.map((item) => ({
    id: item.id || `${item.role}-${item.created_at || Date.now()}`,
    role: item.role,
    content: item.content,
    createdAt: item.created_at || new Date().toISOString(),
  }));

const formatMessageTime = (dateString) => {
  if (!dateString) {
    return "";
  }
  const dt = new Date(dateString);
  if (Number.isNaN(dt.getTime())) {
    return "";
  }
  return dt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
};

const AIChatbot = () => {
  const location = useLocation();
  const [currentUser, setCurrentUser] = useState(() => readCurrentUser());
  const [isOpen, setIsOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [contextSummary, setContextSummary] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [isOnline, setIsOnline] = useState(() => window.navigator.onLine);

  const scrollRef = useRef(null);
  const textareaRef = useRef(null);
  const isAuthenticated = Boolean(currentUser?.id);

  useEffect(() => {
    const syncUser = () => {
      setCurrentUser(readCurrentUser());
    };
    syncUser();
    window.addEventListener("storage", syncUser);
    return () => window.removeEventListener("storage", syncUser);
  }, []);

  useEffect(() => {
    setCurrentUser(readCurrentUser());
  }, [location.pathname]);

  useEffect(() => {
    const onlineHandler = () => setIsOnline(true);
    const offlineHandler = () => setIsOnline(false);
    window.addEventListener("online", onlineHandler);
    window.addEventListener("offline", offlineHandler);
    return () => {
      window.removeEventListener("online", onlineHandler);
      window.removeEventListener("offline", offlineHandler);
    };
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isSending]);

  useEffect(() => {
    if (!textareaRef.current) {
      return;
    }
    textareaRef.current.style.height = "auto";
    textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
  }, [inputValue]);

  useEffect(() => {
    if (isOpen && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }
    const onEscape = (event) => {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    };
    window.addEventListener("keydown", onEscape);
    return () => window.removeEventListener("keydown", onEscape);
  }, [isOpen]);

  const refreshContext = useCallback(async () => {
    try {
      const params = {
        path: location.pathname,
        page_title: document.title || "Sponsorship Hub",
      };
      const response = isAuthenticated ? await fetchAIContext(params) : await fetchPublicAIContext(params);
      setContextSummary(response?.data || null);
    } catch {
      setContextSummary(null);
    }
  }, [isAuthenticated, location.pathname]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    refreshContext();
  }, [isOpen, refreshContext]);

  useEffect(() => {
    let cancelled = false;
    const loadHistory = async () => {
      if (!isOpen) {
        return;
      }
      setErrorMessage("");
      if (!isAuthenticated) {
        setMessages([]);
        return;
      }
      setIsLoadingHistory(true);
      try {
        const response = await fetchAIHistory(120);
        if (cancelled) {
          return;
        }
        const historyMessages = mapHistory(response?.data || []);
        if (historyMessages.length > 0) {
          setMessages(historyMessages);
        } else {
          setMessages([]);
        }
      } catch {
        if (!cancelled) {
          setErrorMessage("Unable to load previous chat right now.");
          setMessages([]);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingHistory(false);
        }
      }
    };
    loadHistory();
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, isOpen]);

  const sendMessage = useCallback(
    async (rawMessage) => {
      const trimmed = rawMessage.trim();
      if (!trimmed || isSending) {
        return;
      }
      setErrorMessage("");
      setInputValue("");

      const optimisticUserMessage = {
        id: `local-user-${Date.now()}`,
        role: "user",
        content: trimmed,
        createdAt: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, optimisticUserMessage]);
      setIsSending(true);

      const pageData = collectPageDataSnapshot(location.pathname);
      const payload = {
        message: trimmed,
        path: location.pathname,
        page_title: document.title || "Sponsorship Hub",
        page_data: pageData,
      };

      try {
        const response = isAuthenticated ? await sendAIMessage(payload) : await sendPublicAIMessage(payload);
        const responseData = response?.data || {};
        if (responseData.context) {
          setContextSummary(responseData.context);
        }
        if (isAuthenticated) {
          const historyMessages = mapHistory(responseData.history || []);
          if (historyMessages.length > 0) {
            setMessages(historyMessages);
          }
        } else {
          const assistantReply = {
            id: `local-ai-${Date.now()}`,
            role: "assistant",
            content: responseData.reply || "I am here to help with product workflows.",
            createdAt: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, assistantReply]);
        }
      } catch (error) {
        const fallbackContent =
          error?.response?.data?.message ||
          "I could not process that right now. Try again in a moment.";
        setMessages((prev) => [
          ...prev,
          {
            id: `local-error-${Date.now()}`,
            role: "assistant",
            content: fallbackContent,
            createdAt: new Date().toISOString(),
          },
        ]);
      } finally {
        setIsSending(false);
      }
    },
    [isAuthenticated, isSending, location.pathname]
  );

  const handleSubmit = (event) => {
    event.preventDefault();
    sendMessage(inputValue);
  };

  const handleInputKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage(inputValue);
    }
  };

  const handleClearHistory = async () => {
    if (!isAuthenticated || isSending) {
      return;
    }
    try {
      await clearAIHistory();
      setMessages([]);
      setErrorMessage("");
    } catch {
      setErrorMessage("Unable to clear chat right now.");
    }
  };

  const contextLine = useMemo(() => {
    if (!contextSummary) {
      return "Context loading...";
    }
    const title = contextSummary.title || "Current Page";
    const role = contextSummary.role || "guest";
    return `${title} • ${role}`;
  }, [contextSummary]);

  const shouldShowPrompts = useMemo(
    () => !isLoadingHistory && !messages.some((message) => message.role === "user"),
    [isLoadingHistory, messages]
  );

  return (
    <div className={`ai-chatbot-wrapper ${isOpen ? "open" : ""}`}>
      <button
        type="button"
        className="ai-chatbot-fab"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-label={isOpen ? "Close AI assistant" : "Open AI assistant"}
        aria-expanded={isOpen}
      >
        {isOpen ? "×" : "AI"}
      </button>

      {isOpen && (
        <section className="ai-chat-panel glass" role="dialog" aria-label="HubBot assistant">
          <header className="ai-chat-header">
            <div className="ai-chat-header-main">
              <h3>HubBot</h3>
              <p className="ai-chat-context-line">{contextLine}</p>
            </div>

            <div className="ai-chat-head-actions">
              <span className={`ai-net-pill ${isOnline ? "online" : "offline"}`}>
                <span className="dot" />
                {isOnline ? "Online" : "Offline"}
              </span>
              {isAuthenticated && (
                <button type="button" className="ai-clear-btn" onClick={handleClearHistory}>
                  Clear
                </button>
              )}
            </div>
          </header>

          {shouldShowPrompts && (
            <div className="ai-quick-prompts">
              {QUICK_PROMPTS.map((prompt) => (
                <button key={prompt} type="button" onClick={() => sendMessage(prompt)} disabled={isSending}>
                  {prompt}
                </button>
              ))}
            </div>
          )}

          {errorMessage ? <p className="ai-chat-error">{errorMessage}</p> : null}

          <div className="ai-chat-body" ref={scrollRef}>
            {isLoadingHistory ? (
              <p className="ai-chat-loading">Loading chat history...</p>
            ) : messages.length === 0 ? (
              <div className="ai-chat-empty">
                Ask your question and I will reply with page-specific guidance.
              </div>
            ) : (
              messages.map((message) => (
                <article key={message.id} className={`ai-chat-message ${message.role === "assistant" ? "assistant" : "user"}`}>
                  <p className="ai-chat-message-text">{message.content}</p>
                  <time className="ai-chat-time">{formatMessageTime(message.createdAt)}</time>
                </article>
              ))
            )}
            {isSending && <p className="ai-chat-loading">HubBot is thinking...</p>}
          </div>

          <form className="ai-chat-form" onSubmit={handleSubmit}>
            <textarea
              ref={textareaRef}
              value={inputValue}
              onChange={(event) => setInputValue(event.target.value)}
              onKeyDown={handleInputKeyDown}
              rows={2}
              maxLength={1800}
              disabled={isSending}
            />
            <button type="submit" disabled={!inputValue.trim() || isSending}>
              Send
            </button>
            <p className="ai-chat-helper">
              {inputValue.length}/1800
            </p>
          </form>

          {!isAuthenticated && (
            <p className="ai-chat-footnote">
              Guest mode is active. Sign in to get personalized stats and saved chat history.
            </p>
          )}
        </section>
      )}
    </div>
  );
};

export default AIChatbot;
