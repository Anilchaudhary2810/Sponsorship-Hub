import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  fetchNotifications,
  markNotificationRead,
  markAllNotificationsRead,
} from "../services/api";
import { WS_BASE_URL } from "../api/api";
import "./NotificationBell.css";

const NotificationBell = () => {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const socketRef = useRef(null);
  const reconnectTimerRef = useRef(null);
  const keyCounterRef = useRef(0);
  const mountedRef = useRef(true);
  const [currentUser] = useState(() => JSON.parse(localStorage.getItem("currentUser") || "{}"));

  const logNotificationError = useCallback((scope, err) => {
    if (err?.response?.status === 401) return;
    console.error(`[NotificationBell] ${scope}`, err);
  }, []);

  const ensureNotificationKey = useCallback((notification) => {
    if (!notification) return notification;
    if (notification._clientKey) return notification;

    if (notification.id !== undefined && notification.id !== null) {
      return { ...notification, _clientKey: `id-${notification.id}` };
    }

    keyCounterRef.current += 1;
    return { ...notification, _clientKey: `tmp-${keyCounterRef.current}` };
  }, []);

  const loadNotifications = useCallback(async () => {
    if (!currentUser?.id) return;

    try {
      const response = await fetchNotifications();
      if (!mountedRef.current) return;

      const normalized = (response.data || []).map(ensureNotificationKey);
      setNotifications(normalized);
      setUnreadCount(normalized.filter((item) => !item.is_read).length);
    } catch (err) {
      logNotificationError("loadNotifications failed", err);
    }
  }, [currentUser?.id, ensureNotificationKey, logNotificationError]);

  const connectWebSocket = useCallback(() => {
    if (!mountedRef.current) return;

    const userId = currentUser.id;
    if (!userId) return;

    if (
      socketRef.current &&
      (socketRef.current.readyState === WebSocket.OPEN ||
        socketRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    const wsUrl = `${WS_BASE_URL}/ws/notifications/${userId}`;
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };

    socket.onmessage = (event) => {
      if (!mountedRef.current) return;

      try {
        const notif = JSON.parse(event.data);

        if (notif.title && notif.message) {
          const normalized = ensureNotificationKey(notif);

          setNotifications((prev) => {
            if (normalized.id && prev.some((item) => item.id === normalized.id)) {
              return prev;
            }
            return [normalized, ...prev];
          });

          if (!normalized.is_read) {
            setUnreadCount((count) => count + 1);
          }

          window.dispatchEvent(new CustomEvent("dashboard-refresh"));
        } else if (notif.type === "DEAL_UPDATE" || notif.type === "MARKETPLACE_REFRESH") {
          loadNotifications();
          window.dispatchEvent(new CustomEvent("dashboard-refresh"));
        }
      } catch (err) {
        console.error("[NotificationBell] malformed websocket frame", err);
      }
    };

    socket.onerror = () => {
      // Let onclose handle reconnect.
    };

    socket.onclose = (event) => {
      if (!mountedRef.current) return;
      if (event.code === 1000 || event.code === 1001) return;

      reconnectTimerRef.current = setTimeout(() => {
        connectWebSocket();
      }, 3000);
    };
  }, [currentUser.id, ensureNotificationKey, loadNotifications]);

  useEffect(() => {
    mountedRef.current = true;
    loadNotifications();
    connectWebSocket();

    return () => {
      mountedRef.current = false;

      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }

      if (socketRef.current) {
        socketRef.current.close(1000, "Component unmounted");
        socketRef.current = null;
      }
    };
  }, [connectWebSocket, loadNotifications]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleMarkRead = async (id) => {
    if (!id) return;

    try {
      await markNotificationRead(id);
      setNotifications((prev) => prev.map((item) => (item.id === id ? { ...item, is_read: true } : item)));
      setUnreadCount((count) => Math.max(0, count - 1));
    } catch (err) {
      logNotificationError("markNotificationRead failed", err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsRead();
      setNotifications((prev) => prev.map((item) => ({ ...item, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      logNotificationError("markAllNotificationsRead failed", err);
    }
  };

  const typeIcon = (type) => {
    if (type === "payment") return "\u{1F4B0}";
    if (type === "deal_new") return "\u{1F91D}";
    if (type === "sign") return "\u270D\uFE0F";
    if (type === "deal_update") return "\u{1F501}";
    return "\u{1F4E9}";
  };

  return (
    <div className="notification-bell-container" ref={dropdownRef}>
      <button className="bell-btn" onClick={() => setIsOpen((prev) => !prev)}>
        <span className="bell-icon">&#128276;</span>
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
              notifications.map((notification, index) => (
                <div
                  key={notification._clientKey || `notif-fallback-${index}`}
                  className={`notif-item ${notification.is_read ? "read" : "unread"}`}
                  onClick={() => !notification.is_read && handleMarkRead(notification.id)}
                >
                  <div className="notif-type-icon">{typeIcon(notification.type)}</div>
                  <div className="notif-content">
                    <p className="notif-title">{notification.title}</p>
                    <p className="notif-msg">{notification.message}</p>
                    <span className="notif-time">
                      {notification.created_at
                        ? new Date(notification.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                        : "just now"}
                    </span>
                  </div>
                  {!notification.is_read && <div className="unread-dot" />}
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
