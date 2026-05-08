/**
 * Agniveer — Admin Tactical Command Hub
 * Fully compatible with self-contained admin.html (no Tailwind)
 */

(function () {
    let detections = [];
    let filteredDetections = [];
    let isRealtime = false;
    let API_BASE_URL = null;

    // ─── Global Actions (called from HTML buttons) ────────────────────────────

    window.deleteIncident = async function (id) {
        if (!confirm('Permanently delete this incident?')) return;
        showToast('Initiating deletion…', 'info');
        try {
            const res = await fetch(`${API_BASE_URL}/detections/${id}`, { method: 'DELETE' });
            if (res.ok || res.status === 404) {
                // Also remove from Firestore
                if (typeof firebase !== 'undefined' && firebase.apps.length > 0) {
                    try { await firebase.firestore().collection('detections').doc(id).delete(); }
                    catch (e) { console.warn('Firestore delete:', e); }
                }
                detections = detections.filter(d => d.id !== id);
                applyFilter();
                updateStats();
                showToast('Incident deleted successfully.', 'success');
                if (!isRealtime) fetchData();
            } else {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || `HTTP ${res.status}`);
            }
        } catch (e) {
            console.error(e);
            showToast(`Delete failed: ${e.message}`, 'error');
        }
    };

    window.resolveIncident = async function (id) {
        if (!confirm('Mark this incident as resolved?')) return;
        showToast('Sending resolve signal…', 'info');
        try {
            const res = await fetch(`${API_BASE_URL}/detections/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'resolved' })
            });
            if (res.ok) {
                if (typeof firebase !== 'undefined' && firebase.apps.length > 0) {
                    try { await firebase.firestore().collection('detections').doc(id).update({ status: 'resolved' }); }
                    catch (e) { console.warn('Firestore update:', e); }
                }
                const target = detections.find(d => d.id === id);
                if (target) target.status = 'resolved';
                applyFilter();
                updateStats();
                showToast('Incident marked as resolved.', 'success');
                if (!isRealtime) fetchData();
            } else {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || `HTTP ${res.status}`);
            }
        } catch (e) {
            showToast(`Resolve failed: ${e.message}`, 'error');
        }
    };

    window.verifyIncident = async function (id) {
        if (!confirm('Mark this incident as VERIFIED?')) return;
        showToast('Sending verify signal…', 'info');
        try {
            const res = await fetch(`${API_BASE_URL}/detections/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'verified' })
            });
            if (res.ok) {
                if (typeof firebase !== 'undefined' && firebase.apps.length > 0) {
                    try { await firebase.firestore().collection('detections').doc(id).update({ status: 'verified' }); }
                    catch (e) { console.warn('Firestore update:', e); }
                }
                const target = detections.find(d => d.id === id);
                if (target) target.status = 'verified';
                applyFilter();
                updateStats();
                showToast('Incident marked as verified.', 'success');
                if (!isRealtime) fetchData();
            } else {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || `HTTP ${res.status}`);
            }
        } catch (e) {
            showToast(`Verify failed: ${e.message}`, 'error');
        }
    };

    window.markFalseAlarm = async function (id) {
        if (!confirm('Mark this incident as FALSE ALARM?')) return;
        showToast('Marking as false alarm…', 'info');
        try {
            const res = await fetch(`${API_BASE_URL}/detections/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'false_alarm' })
            });
            if (res.ok) {
                if (typeof firebase !== 'undefined' && firebase.apps.length > 0) {
                    try { await firebase.firestore().collection('detections').doc(id).update({ status: 'false_alarm' }); }
                    catch (e) { console.warn('Firestore update:', e); }
                }
                const target = detections.find(d => d.id === id);
                if (target) target.status = 'false_alarm';
                applyFilter();
                updateStats();
                showToast('Incident marked as false alarm.', 'success');
                if (!isRealtime) fetchData();
            } else {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || `HTTP ${res.status}`);
            }
        } catch (e) {
            showToast(`Update failed: ${e.message}`, 'error');
        }
    };

    window.purgeAllDetections = async function () {
        if (!confirm('CRITICAL: Purge ALL incidents from system?')) return;
        showToast('Master purge initiated…', 'info');
        try {
            for (const d of [...detections]) {
                try { await fetch(`${API_BASE_URL}/detections/${d.id}`, { method: 'DELETE' }); } catch (_) {}
                if (typeof firebase !== 'undefined' && firebase.apps.length > 0) {
                    try { await firebase.firestore().collection('detections').doc(d.id).delete(); } catch (_) {}
                }
            }
            detections = [];
            filteredDetections = [];
            renderTable();
            updateStats();
            showToast('All incidents purged.', 'success');
        } catch (e) {
            showToast(`Purge failed: ${e.message}`, 'error');
        }
    };

    window.filterTable = function () {
        applyFilter();
    };

    // ─── Init ────────────────────────────────────────────────────────────────

    document.addEventListener('DOMContentLoaded', async () => {
        if (window.API_CONFIG && window.API_CONFIG.ready) {
            await window.API_CONFIG.ready;
        }
        API_BASE_URL = window.API_CONFIG
            ? window.API_CONFIG.baseUrl
            : `http://${window.location.hostname || 'localhost'}:8000/api`;

        startClock();
        await fetchData();

        // ✅ ALWAYS poll every 3 seconds (guaranteed fresh data)
        startPolling();

        // ✅ ALSO try Firebase for instant real-time updates
        try {
            const ok = await initializeFirebase();
            if (ok && typeof firebase !== 'undefined' && firebase.apps.length > 0) {
                isRealtime = true;
                updateSyncLabel(true);
                setupRealtimeListeners();
                loadCitizenReports(); // ← citizen report listener
            } else {
                updateSyncLabel(false);
                loadCitizenReports(); // still show "not connected" message
            }
        } catch (_) {
            updateSyncLabel(false);
        }
    });

    function updateSyncLabel(realtime) {
        const el = document.getElementById('syncStatusLabel');
        if (!el) return;
        el.textContent = realtime ? 'Firebase Sync Active' : 'Polling Mode';
    }

    function startClock() {
        const el = document.getElementById('currentTime');
        if (!el) return;
        const tick = () => { el.textContent = new Date().toLocaleTimeString([], { hour12: false }); };
        tick();
        setInterval(tick, 1000);
    }

    function startPolling() { setInterval(fetchData, 3000); }

    async function fetchData() {
        try {
            const res = await fetch(`${API_BASE_URL}/detections/?limit=100`);
            if (!res.ok) throw new Error(`API error ${res.status}`);
            detections = await res.json();
            applyFilter();
            updateStats();
        } catch (e) {
            console.warn('Polling error:', e.message);
        }
    }

    function setupRealtimeListeners() {
        if (typeof firebase === 'undefined') return;
        firebase.firestore().collection('detections')
            .orderBy('timestamp', 'desc')
            .onSnapshot(snapshot => {
                snapshot.docChanges().forEach(change => {
                    const id = change.doc.id;
                    const data = { id, ...change.doc.data() };
                    if (change.type === 'added') {
                        if (!detections.find(d => d.id === id)) detections.unshift(data);
                    } else if (change.type === 'modified') {
                        const i = detections.findIndex(d => d.id === id);
                        if (i !== -1) detections[i] = data;
                    } else if (change.type === 'removed') {
                        detections = detections.filter(d => d.id !== id);
                    }
                });
                applyFilter();
                updateStats();
            }, err => {
                console.error('Snapshot error:', err);
                isRealtime = false;
                updateSyncLabel(false);
                startPolling();
            });
    }

    // ─── Filter ──────────────────────────────────────────────────────────────

    function applyFilter() {
        const q = (document.getElementById('searchInput')?.value || '').toLowerCase();
        filteredDetections = q
            ? detections.filter(d =>
                (d.address || '').toLowerCase().includes(q) ||
                (d.id || '').toLowerCase().includes(q) ||
                (d.city || '').toLowerCase().includes(q) ||
                (d.status || '').toLowerCase().includes(q))
            : [...detections];
        renderTable();
    }

    // ─── Stats ───────────────────────────────────────────────────────────────

    function updateStats() {
        const active = detections.filter(d => d.status === 'pending' || d.status === 'verified').length;
        const activeEl = document.getElementById('stats-active');
        const totalEl  = document.getElementById('stats-total');
        if (activeEl) activeEl.textContent = active;
        if (totalEl)  totalEl.textContent  = detections.length;
    }

    // ─── Table Render ────────────────────────────────────────────────────────

    function renderTable() {
        const tbody = document.getElementById('adminIncidentTable');
        if (!tbody) return;

        if (filteredDetections.length === 0) {
            tbody.innerHTML = `<tr class="empty-row"><td colspan="6">No incidents found in system</td></tr>`;
            return;
        }

        tbody.innerHTML = filteredDetections.map(d => {
            const confidence = Math.round((parseFloat(d.confidence) || 0) * 100);
            const date = d.timestamp ? new Date(d.timestamp).toLocaleString() : 'N/A';

            // Address: prefer full address, else city/state, else coords, else fallback
            let region = d.address || '';
            if (!region || region === 'Mobile Surveillance Node') {
                if (d.city || d.state) region = [d.city, d.state].filter(Boolean).join(', ');
                else if (d.latitude && d.longitude) region = 'Mobile Surveillance Node';
                else region = 'Unknown Location';
            }

            // GPS display
            const gps = (d.latitude && d.longitude && (d.latitude !== 0 || d.longitude !== 0))
                ? `<a href="https://maps.google.com/?q=${d.latitude},${d.longitude}" target="_blank"
                       style="color:#3B82F6;font-size:10px;font-family:monospace;text-decoration:none;" title="Open in Google Maps">
                       📍 ${parseFloat(d.latitude).toFixed(4)}, ${parseFloat(d.longitude).toFixed(4)}
                   </a>`
                : `<span style="color:#475569;font-size:10px;">No GPS</span>`;

            const status = (d.status || 'pending').toLowerCase();
            const statusBadge = `<span class="status-badge ${status}">${status}</span>`;

            const barColor = confidence >= 80 ? '#F43F5E' : confidence >= 60 ? '#F59E0B' : '#10B981';

            return `
            <tr>
              <td>
                <div class="region-name">${escHtml(region)}</div>
                <div class="region-id">${escHtml(d.id)}</div>
              </td>
              <td>
                <div class="confidence-bar">
                  <div class="bar-track">
                    <div class="bar-fill" style="width:${confidence}%;background:${barColor}"></div>
                  </div>
                  <span class="conf-value" style="color:${barColor}">${confidence}%</span>
                </div>
              </td>
              <td><span class="timestamp">${date}</span></td>
              <td>${gps}</td>
              <td>${statusBadge}</td>
              <td>
                <div class="actions">
                  <button class="action-btn btn-verify" onclick="verifyIncident('${d.id}')">
                    <span class="material-symbols-outlined">verified</span> Verify
                  </button>
                  <button class="action-btn btn-resolve" onclick="resolveIncident('${d.id}')">
                    <span class="material-symbols-outlined">check_circle</span> Resolve
                  </button>
                  <button class="action-btn btn-false" onclick="markFalseAlarm('${d.id}')">
                    <span class="material-symbols-outlined">block</span> False Alarm
                  </button>
                  <button class="action-btn btn-delete" onclick="deleteIncident('${d.id}')">
                    <span class="material-symbols-outlined">delete</span> Delete
                  </button>
                </div>
              </td>
            </tr>`;
        }).join('');
    }

    // ─── Toast ───────────────────────────────────────────────────────────────

    function showToast(msg, type = 'info') {
        const container = document.getElementById('toastContainer');
        if (!container) return;
        const icons = { success: 'check_circle', error: 'cancel', info: 'info' };
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <div class="toast-icon"><span class="material-symbols-outlined">${icons[type] || 'info'}</span></div>
            <span>${escHtml(msg)}</span>`;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(20px)';
            toast.style.transition = 'all 0.4s';
            setTimeout(() => toast.remove(), 400);
        }, 4000);
    }

    function escHtml(str) {
        return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    // ─── Citizen Reports ─────────────────────────────────────────────────────

    window.dismissCitizenReport = async function(docId) {
        if (!confirm('Mark this citizen report as reviewed?')) return;
        try {
            if (typeof firebase !== 'undefined' && firebase.apps.length > 0) {
                await firebase.firestore().collection('citizen_reports').doc(docId).update({ status: 'reviewed' });
                showToast('Report marked as reviewed.', 'success');
            } else {
                showToast('Firebase not connected.', 'error');
            }
        } catch(e) { showToast('Failed: ' + e.message, 'error'); }
    };

    function loadCitizenReports() {
        if (typeof firebase === 'undefined' || firebase.apps.length === 0) {
            const tbody = document.getElementById('citizenReportTable');
            if (tbody) tbody.innerHTML = '<tr class="empty-row"><td colspan="6">Firebase not connected — citizen reports unavailable.</td></tr>';
            return;
        }

        firebase.firestore().collection('citizen_reports')
            .orderBy('timestamp', 'desc')
            .onSnapshot(snapshot => {
                const reports = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
                renderCitizenTable(reports);
                const countEl = document.getElementById('stats-citizen');
                if (countEl) countEl.textContent = reports.length;
            }, err => {
                console.error('Citizen reports error:', err);
            });
    }

    function renderCitizenTable(reports) {
        const tbody = document.getElementById('citizenReportTable');
        if (!tbody) return;

        if (reports.length === 0) {
            tbody.innerHTML = '<tr class="empty-row"><td colspan="6">No citizen reports yet.</td></tr>';
            return;
        }

        tbody.innerHTML = reports.map(r => {
            const date = r.timestamp ? new Date(r.timestamp).toLocaleString() : 'N/A';
            const gps = r.latitude && r.longitude
                ? `<a href="https://maps.google.com/?q=${r.latitude},${r.longitude}" target="_blank"
                       style="color:#3B82F6;font-size:10px;font-family:monospace;text-decoration:none;">
                       📍 ${parseFloat(r.latitude).toFixed(4)}, ${parseFloat(r.longitude).toFixed(4)}</a>`
                : `<span style="color:#475569;font-size:10px;">No GPS</span>`;

            const isReviewed = (r.status || '') === 'reviewed';
            const badge = isReviewed
                ? `<span class="status-badge resolved">Reviewed</span>`
                : `<span class="status-badge pending">New</span>`;

            return `
            <tr>
              <td><div class="region-name">${escHtml(r.location || 'Unknown')}</div></td>
              <td><div style="font-size:11px;color:#94a3b8;max-width:280px">${escHtml(r.description || '—')}</div></td>
              <td><span class="timestamp">${date}</span></td>
              <td>${gps}</td>
              <td>${badge}</td>
              <td>
                <div class="actions">
                  ${!isReviewed ? `<button class="action-btn btn-resolve" onclick="dismissCitizenReport('${r.id}')">
                    <span class="material-symbols-outlined">check_circle</span> Mark Reviewed
                  </button>` : ''}
                  <button class="action-btn btn-delete" onclick="deleteCitizenReport('${r.id}')">
                    <span class="material-symbols-outlined">delete</span> Delete
                  </button>
                </div>
              </td>
            </tr>`;
        }).join('');
    }

    window.deleteCitizenReport = async function(docId) {
        if (!confirm('Delete this citizen report permanently?')) return;
        try {
            await firebase.firestore().collection('citizen_reports').doc(docId).delete();
            showToast('Citizen report deleted.', 'success');
        } catch(e) { showToast('Delete failed: ' + e.message, 'error'); }
    };

})();
