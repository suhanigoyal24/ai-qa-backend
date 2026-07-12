/* api.js — API base URL, JWT token storage, and the shared fetch wrapper.
   Loaded on every page (index, login, signup). */

const API_BASE_URL = 'http://localhost:8000/api';

const TOKEN_KEYS = {
  access: 'aiqa_access_token',
  refresh: 'aiqa_refresh_token',
  username: 'aiqa_username'
};

function getAccessToken() {
  return localStorage.getItem(TOKEN_KEYS.access);
}

function getRefreshToken() {
  return localStorage.getItem(TOKEN_KEYS.refresh);
}

function setAccessToken(access) {
  localStorage.setItem(TOKEN_KEYS.access, access);
}

function getUsername() {
  return localStorage.getItem(TOKEN_KEYS.username);
}

function setSession({ access, refresh, username }) {
  localStorage.setItem(TOKEN_KEYS.access, access);
  localStorage.setItem(TOKEN_KEYS.refresh, refresh);
  localStorage.setItem(TOKEN_KEYS.username, username);
}

function clearSession() {
  localStorage.removeItem(TOKEN_KEYS.access);
  localStorage.removeItem(TOKEN_KEYS.refresh);
  localStorage.removeItem(TOKEN_KEYS.username);
}

function isLoggedIn() {
  return !!getAccessToken();
}

function redirectToLogin() {
  clearSession();
  window.location.href = 'login.html';
}

/**
 * Exchanges the stored refresh token for a new access token.
 * Returns true on success, false if the refresh token is missing/invalid.
 */
async function refreshAccessToken() {
  const refresh = getRefreshToken();
  if (!refresh) return false;

  try {
    const res = await fetch(`${API_BASE_URL}/auth/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh })
    });
    if (!res.ok) return false;

    const data = await res.json();
    setAccessToken(data.access);
    return true;
  } catch {
    return false;
  }
}

/**
 * Wrapper around fetch() that attaches the JWT access token to every
 * request. On a 401, it tries one silent refresh and retries the request
 * once before giving up and sending the user back to login.html.
 * Use this instead of raw fetch() for every call to API_BASE_URL.
 */
async function apiFetch(path, options = {}, isRetry = false) {
  const token = getAccessToken();
  const headers = { ...(options.headers || {}) };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    if (!isRetry && await refreshAccessToken()) {
      return apiFetch(path, options, true);
    }
    redirectToLogin();
    throw new Error('Session expired. Please log in again.');
  }

  return res;
}