/* auth.js — login.html and signup.html form handlers. */

async function handleLogin(e) {
  e.preventDefault();
  const submitBtn = document.getElementById('auth-submit');
  const errorEl = document.getElementById('auth-error');
  errorEl.textContent = '';
  submitBtn.disabled = true;

  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value;

  try {
    const res = await fetch(`${API_BASE_URL}/auth/login/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Login failed');

    setSession({ access: data.access, refresh: data.refresh, username: data.username });
    window.location.href = 'index.html';
  } catch (err) {
    errorEl.textContent = err.message || 'Login failed';
    submitBtn.disabled = false;
  }
}

async function handleSignup(e) {
  e.preventDefault();
  const submitBtn = document.getElementById('auth-submit');
  const errorEl = document.getElementById('auth-error');
  errorEl.textContent = '';
  submitBtn.disabled = true;

  const username = document.getElementById('username').value.trim();
  const email = document.getElementById('email').value.trim();
  const password = document.getElementById('password').value;

  try {
    const res = await fetch(`${API_BASE_URL}/auth/register/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Signup failed');

    setSession({ access: data.access, refresh: data.refresh, username: data.username });
    window.location.href = 'index.html';
  } catch (err) {
    errorEl.textContent = err.message || 'Signup failed';
    submitBtn.disabled = false;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  if (isLoggedIn()) {
    window.location.href = 'index.html';
    return;
  }

  const loginForm = document.getElementById('login-form');
  if (loginForm) loginForm.addEventListener('submit', handleLogin);

  const signupForm = document.getElementById('signup-form');
  if (signupForm) signupForm.addEventListener('submit', handleSignup);
});