/**
 * NCPS Webapp — Core Application Logic
 * User identity, permissions, location tracking, API service.
 */

const API = window.location.origin;

// ═══════════════════════════════════════════════════════
// User Identity (auto-generated UUID, persisted in localStorage)
// ═══════════════════════════════════════════════════════

function getUserId() {
  let uid = localStorage.getItem('ncps_user_id');
  if (!uid) {
    uid = crypto.randomUUID ? crypto.randomUUID() : _uuidv4();
    localStorage.setItem('ncps_user_id', uid);
  }
  return uid;
}

function _uuidv4() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
    const r = Math.random() * 16 | 0;
    return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
  });
}

// ═══════════════════════════════════════════════════════
// Preferences
// ═══════════════════════════════════════════════════════

function getPrefs() {
  const raw = localStorage.getItem('ncps_prefs');
  return raw ? JSON.parse(raw) : {
    location_enabled: false,
    notifications_enabled: false,
    onboarded: false,
  };
}

function savePrefs(prefs) {
  localStorage.setItem('ncps_prefs', JSON.stringify(prefs));
}

// ═══════════════════════════════════════════════════════
// Location Tracking
// ═══════════════════════════════════════════════════════

let currentLocation = { lat: null, lon: null };
let locationWatchId = null;

function startLocationTracking() {
  if (!navigator.geolocation) return;

  const prefs = getPrefs();
  if (!prefs.location_enabled) return;

  locationWatchId = navigator.geolocation.watchPosition(
    (pos) => {
      currentLocation.lat = pos.coords.latitude;
      currentLocation.lon = pos.coords.longitude;

      // Send to backend
      apiCall('/api/user/location', 'POST', {
        user_id: getUserId(),
        lat: currentLocation.lat,
        lon: currentLocation.lon,
      }).catch(() => {});

      // Update UI indicator
      updateLocationIndicator(true);
    },
    (err) => {
      console.warn('Geolocation error:', err.message);
      updateLocationIndicator(false);
    },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 }
  );
}

function stopLocationTracking() {
  if (locationWatchId !== null) {
    navigator.geolocation.clearWatch(locationWatchId);
    locationWatchId = null;
  }
  updateLocationIndicator(false);
}

function updateLocationIndicator(active) {
  const el = document.getElementById('location-indicator');
  if (!el) return;
  if (active && currentLocation.lat) {
    el.className = 'location-indicator';
    el.innerHTML = '<span class="dot"></span> ' +
      currentLocation.lat.toFixed(2) + ', ' + currentLocation.lon.toFixed(2);
  } else {
    el.className = 'location-indicator off';
    el.innerHTML = '<span class="dot"></span> Location off';
  }
}

// ═══════════════════════════════════════════════════════
// API Service
// ═══════════════════════════════════════════════════════

async function apiCall(path, method = 'GET', body = null) {
  const opts = { method, headers: {} };
  if (body) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }

  let url = API + path;
  if (method === 'GET' && body) {
    const params = new URLSearchParams(body);
    url += '?' + params.toString();
  }

  const res = await fetch(url, opts);
  if (!res.ok) throw new Error('API error: ' + res.status);
  return res.json();
}

// ═══════════════════════════════════════════════════════
// Toast Notifications
// ═══════════════════════════════════════════════════════

function showToast(message, type = 'info') {
  let toast = document.getElementById('app-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'app-toast';
    document.body.appendChild(toast);
  }
  toast.className = 'toast toast-' + type;
  toast.textContent = message;

  requestAnimationFrame(() => {
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
  });
}

// ═══════════════════════════════════════════════════════
// Permissions Modal
// ═══════════════════════════════════════════════════════

function showPermissionsModal() {
  const prefs = getPrefs();
  if (prefs.onboarded) return;

  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.id = 'permissions-modal';
  overlay.innerHTML = `
    <div class="modal-content">
      <div class="modal-title">Welcome to NCPS</div>
      <div class="modal-subtitle">
        NCPS is a trust-aware information platform. We score content by <strong>credibility</strong>, 
        not engagement. To work at its best, we need a few permissions.
      </div>

      <div class="permission-item" id="perm-location">
        <div class="permission-icon">📍</div>
        <div class="permission-info">
          <h4>Location Access</h4>
          <p>Used to show nearby reports, compute proximity-based credibility, 
             and detect location inconsistencies. Your location is <strong>never shared</strong> 
             with other users.</p>
          <div class="permission-toggle">
            <button class="perm-btn" onclick="grantLocation()" id="btn-loc-allow">Allow</button>
            <button class="perm-btn" onclick="skipLocation()" id="btn-loc-skip">Skip</button>
          </div>
        </div>
      </div>

      <div class="permission-item" id="perm-notif">
        <div class="permission-icon">🔔</div>
        <div class="permission-info">
          <h4>Notifications</h4>
          <p>Receive alerts for urgent, credible reports near you. Only high-confidence, 
             high-urgency posts trigger alerts.</p>
          <div class="permission-toggle">
            <button class="perm-btn" onclick="grantNotifications()" id="btn-notif-allow">Allow</button>
            <button class="perm-btn" onclick="skipNotifications()" id="btn-notif-skip">Skip</button>
          </div>
        </div>
      </div>

      <button class="btn btn-primary btn-block mt-24" onclick="finishOnboarding()" id="btn-start">
        Get Started →
      </button>
    </div>
  `;

  document.body.appendChild(overlay);
}

async function grantLocation() {
  try {
    const pos = await new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 10000 });
    });

    currentLocation.lat = pos.coords.latitude;
    currentLocation.lon = pos.coords.longitude;

    const prefs = getPrefs();
    prefs.location_enabled = true;
    savePrefs(prefs);

    const btn = document.getElementById('btn-loc-allow');
    btn.className = 'perm-btn allowed';
    btn.textContent = '✓ Allowed';
    document.getElementById('btn-loc-skip').style.display = 'none';

    showToast('Location access granted', 'success');
  } catch (e) {
    showToast('Location permission denied by browser', 'error');
  }
}

function skipLocation() {
  const prefs = getPrefs();
  prefs.location_enabled = false;
  savePrefs(prefs);

  const btn = document.getElementById('btn-loc-skip');
  btn.className = 'perm-btn skipped';
  btn.textContent = '✓ Skipped';
  document.getElementById('btn-loc-allow').style.display = 'none';
}

async function grantNotifications() {
  if ('Notification' in window) {
    const permission = await Notification.requestPermission();
    if (permission === 'granted') {
      const prefs = getPrefs();
      prefs.notifications_enabled = true;
      savePrefs(prefs);

      const btn = document.getElementById('btn-notif-allow');
      btn.className = 'perm-btn allowed';
      btn.textContent = '✓ Allowed';
      document.getElementById('btn-notif-skip').style.display = 'none';

      showToast('Notifications enabled', 'success');
      return;
    }
  }
  showToast('Notification permission denied', 'error');
}

function skipNotifications() {
  const prefs = getPrefs();
  prefs.notifications_enabled = false;
  savePrefs(prefs);

  const btn = document.getElementById('btn-notif-skip');
  btn.className = 'perm-btn skipped';
  btn.textContent = '✓ Skipped';
  document.getElementById('btn-notif-allow').style.display = 'none';
}

function finishOnboarding() {
  const prefs = getPrefs();
  prefs.onboarded = true;
  savePrefs(prefs);

  const modal = document.getElementById('permissions-modal');
  if (modal) modal.remove();

  // Register user with backend
  apiCall('/api/register', 'POST', { user_id: getUserId() }).catch(() => {});

  // Start location if allowed
  if (prefs.location_enabled) {
    startLocationTracking();
  }

  // Trigger page-specific init
  if (typeof onAppReady === 'function') {
    onAppReady();
  }
}

// ═══════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════

function scoreColor(v) {
  if (v >= 0.7) return '#10b981';
  if (v >= 0.4) return '#f59e0b';
  return '#ef4444';
}

function timeAgo(isoStr) {
  if (!isoStr) return '';
  const diff = (Date.now() - new Date(isoStr).getTime()) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
  if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
  return Math.floor(diff / 86400) + 'd ago';
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function formatDistance(meters) {
  if (!meters && meters !== 0) return '';
  if (meters < 1000) return meters + ' m';
  return (meters / 1000).toFixed(1) + ' km';
}

// ═══════════════════════════════════════════════════════
// Init
// ═══════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
  // Register user
  apiCall('/api/register', 'POST', { user_id: getUserId() }).catch(() => {});

  const prefs = getPrefs();

  // Show permissions modal if not onboarded
  if (!prefs.onboarded) {
    showPermissionsModal();
  } else {
    // Start location tracking if allowed
    if (prefs.location_enabled) {
      startLocationTracking();
    }

    // Trigger page-specific init
    if (typeof onAppReady === 'function') {
      onAppReady();
    }
  }
});
