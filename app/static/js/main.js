/* =====================================================
   GymPro — Main JavaScript
   ===================================================== */

// ── Sidebar Toggle ──
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

// Close sidebar on outside click (mobile)
document.addEventListener('click', function(e) {
  const sidebar = document.getElementById('sidebar');
  const toggle = document.querySelector('.sidebar-toggle');
  if (sidebar && toggle && window.innerWidth <= 768) {
    if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
      sidebar.classList.remove('open');
    }
  }
});

// ── Notification Panel ──
const notifToggle = document.getElementById('notif-toggle');
const notifPanel = document.getElementById('notif-panel');

if (notifToggle && notifPanel) {
  notifToggle.addEventListener('click', (e) => {
    e.stopPropagation();
    notifPanel.classList.toggle('open');
  });
  document.addEventListener('click', (e) => {
    if (!notifPanel.contains(e.target) && !notifToggle.contains(e.target)) {
      notifPanel.classList.remove('open');
    }
  });
}

async function readNotif(id) {
  await fetch(`/api/notifications/read/${id}`, { method: 'POST' });
  const el = document.getElementById(`notif-${id}`);
  if (el) el.style.opacity = '0.4';
  updateBadge(-1);
}

async function deleteNotif(id) {
  await fetch(`/api/notifications/delete/${id}`, { method: 'POST' });
  const el = document.getElementById(`notif-${id}`);
  if (el) { el.style.transition = 'all 0.3s'; el.style.maxHeight = '0'; el.style.overflow = 'hidden'; setTimeout(() => el.remove(), 300); }
  updateBadge(-1);
}

async function markAllRead() {
  await fetch('/api/notifications/read-all', { method: 'POST' });
  document.querySelectorAll('.notif-item').forEach(el => el.style.opacity = '0.4');
  const badge = document.querySelector('.notif-badge');
  if (badge) badge.remove();
}

function updateBadge(delta) {
  const badge = document.querySelector('.notif-badge');
  if (badge) {
    const current = parseInt(badge.textContent) + delta;
    if (current <= 0) badge.remove();
    else badge.textContent = current;
  }
}

// ── Global Search ──
const globalSearch = document.getElementById('global-search');
const searchResults = document.getElementById('search-results');
let searchTimer;

if (globalSearch && searchResults) {
  globalSearch.addEventListener('input', () => {
    clearTimeout(searchTimer);
    const q = globalSearch.value.trim();
    if (!q) { searchResults.classList.remove('show'); return; }
    searchTimer = setTimeout(async () => {
      const res = await fetch(`/api/members/search?q=${encodeURIComponent(q)}`);
      const members = await res.json();
      if (members.length === 0) {
        searchResults.innerHTML = '<div class="search-result-item" style="color:var(--text3);justify-content:center">No results found</div>';
      } else {
        searchResults.innerHTML = members.map(m => `
          <a href="/members/${m.id}" class="search-result-item">
            <div class="member-avatar-sm">${m.full_name[0].toUpperCase()}</div>
            <div>
              <div style="font-size:14px;font-weight:500">${m.full_name}</div>
              <div style="font-size:12px;color:var(--text3)">${m.member_id} · ${m.mobile}</div>
            </div>
            <span class="status-badge status-${m.status.toLowerCase().replace(' ','-')}" style="margin-left:auto">${m.status}</span>
          </a>
        `).join('');
      }
      searchResults.classList.add('show');
    }, 300);
  });

  document.addEventListener('click', (e) => {
    if (!globalSearch.contains(e.target) && !searchResults.contains(e.target)) {
      searchResults.classList.remove('show');
    }
  });

  globalSearch.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { searchResults.classList.remove('show'); globalSearch.value = ''; }
  });
}

// ── Auto-dismiss flash toasts ──
document.querySelectorAll('.toast-msg').forEach(toast => {
  setTimeout(() => {
    toast.style.transition = 'all 0.4s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-10px)';
    setTimeout(() => toast.remove(), 400);
  }, 4000);
});

// ── Keyboard shortcut: Ctrl+K for search ──
document.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    const gs = document.getElementById('global-search');
    if (gs) gs.focus();
  }
});

// ── Update sidebar member count ──
(async () => {
  try {
    const res = await fetch('/api/members/search?q=');
    // just show total from page if available
    const totalEl = document.querySelector('[data-count]');
    const sidebarTotal = document.getElementById('sidebar-total');
    if (sidebarTotal && totalEl) {
      sidebarTotal.textContent = totalEl.dataset.count;
    }
  } catch(e) {}
})();

// ── Smooth page transitions ──
document.querySelectorAll('a:not([target])').forEach(link => {
  if (link.hostname === location.hostname && !link.href.includes('export') && !link.href.includes('backup')) {
    link.addEventListener('click', () => {
      document.body.style.opacity = '0.7';
      document.body.style.transition = 'opacity 0.15s';
    });
  }
});
window.addEventListener('pageshow', () => {
  document.body.style.opacity = '1';
});
