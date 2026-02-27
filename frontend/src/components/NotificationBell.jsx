import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  fetchNotifications,
  markNotificationRead,
  markAllNotificationsRead
} from '../services/api';
import './NotificationBell.css';

const NotificationBell = () => {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const socketRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const mountedRef = useRef(true);
  const [currentUser] = useState(() => JSON.parse(localStorage.getItem("currentUser") || "{}"));

  const loadNotifications = useCallback(async () => {
    try {
      const response = await fetchNotifications();
      if (!mountedRef.current) return;
      setNotifications(response.data);
      setUnreadCount(response.data.filter(n => !n.is_read).length);
    } catch (err) {
      // silently fail — user may not be logged in yet
    }
  }, []);

  // ── WebSocket with auto-reconnect ──────────────────────────────────────
  const connectWebSocket = useCallback(() => {
    if (!mountedRef.current) return;

    const token = localStorage.getItem("authToken");
    const userId = currentUser.id;
    if (!userId || !token) return;

    // Don't open a second socket if one is already open/connecting
    if (
      socketRef.current &&
      (socketRef.current.readyState === WebSocket.OPEN ||
        socketRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    const apiBase = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
    const wsHost = apiBase.replace(/^http/, "ws");
    const wsUrl = `${wsHost}/ws/notifications/${userId}?token=${token}`;
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      // Clear any pending reconnect when connection succeeds
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };

    socket.onmessage = (event) => {
      if (!mountedRef.current) return;
      try {
        const notif = JSON.parse(event.data);
        // Push real-time notification into list and bump badge
        if (notif.title && notif.message) {
          setNotifications(prev => [notif, ...prev]);
          setUnreadCount(c => c + 1);
        } else if (notif.type === "DEAL_UPDATE" || notif.type === "MARKETPLACE_REFRESH") {
          // Just refresh the list for generic deal-update pings
          loadNotifications();
        }
      } catch { /* ignore malformed frames */ }
    };

    socket.onerror = () => {
      // onerror always fires before onclose — just let onclose handle reconnect
    };

    socket.onclose = (event) => {
      if (!mountedRef.current) return;
      // Don't reconnect for explicit client-side close (e.g. logout/unmount)
      if (event.code === 1000 || event.code === 1001) return;
      // Reconnect after 3 s with exponential back-off can be added later
      reconnectTimerRef.current = setTimeout(() => {
        connectWebSocket();
      }, 3000);
    };
  }, [currentUser.id, loadNotifications]);

  useEffect(() => {
    mountedRef.current = true;
    loadNotifications();
    connectWebSocket();

    return () => {
      mountedRef.current = false;
      // Cancel any pending reconnect
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      // Cleanly close socket with normal close code so onclose won't reconnect
      if (socketRef.current) {
        socketRef.current.close(1000, "Component unmounted");
        socketRef.current = null;
      }
    };
  }, [currentUser.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Click-outside to close dropdown ───────────────────────────────────
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // ── Mark handlers ──────────────────────────────────────────────────────
  const handleMarkRead = async (id) => {
    try {
      await markNotificationRead(id);
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
      setUnreadCount(c => Math.max(0, c - 1));
    } catch { /* ignore */ }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsRead();
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch { /* ignore */ }
  };

  // ── Type → icon mapping ────────────────────────────────────────────────
  const typeIcon = (type) => {
    if (type === 'payment') return '💰';
    if (type === 'deal_new') return '🤝';
    if (type === 'sign') return '✍️';
    if (type === 'deal_update') return '🔄';
    return '📩';
  };

  return (
    <div className="notification-bell-container" ref={dropdownRef}>
      <button className="bell-btn" onClick={() => setIsOpen(prev => !prev)}>
        <span className="bell-icon">🔔</span>
        {unreadCount > 0 && <span className="unread-badge">{unreadCount}</span>}
      </button>

      {isOpen && (
        <div className="notification-dropdown glass-morphism">
          <div className="notif-header">
            <h3>Notifications</h3>
            {unreadCount > 0 && (
              <button className="mark-all-btn" onClick={handleMarkAllRead}>
                Mark all read
              </button>
            )}
          </div>
          <div className="notif-list">
            {notifications.length === 0 ? (
              <div className="empty-notif">No new updates</div>
            ) : (
              notifications.map(n => (
                <div
                  key={n.id ?? Math.random()}
                  className={`notif-item ${n.is_read ? 'read' : 'unread'}`}
                  onClick={() => !n.is_read && handleMarkRead(n.id)}
                >
                  <div className="notif-type-icon">{typeIcon(n.type)}</div>
                  <div className="notif-content">
                    <p className="notif-title">{n.title}</p>
                    <p className="notif-msg">{n.message}</p>
                    <span className="notif-time">
                      {n.created_at
                        ? new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                        : 'just now'}
                    </span>
                  </div>
                  {!n.is_read && <div className="unread-dot" />}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationBell;
