const API_URL = window.API_URL || 'http://localhost:5001';
const audio = document.getElementById('audio');
const playBtn = document.getElementById('playBtn');
const statusDiv = document.getElementById('status');

let isPlaying = false;
let hls = null;
let currentUser = null;
let authToken = null;
let selectedFile = null;
let allTracks = [];
let confirmResolve = null;

// Track duration and timing
let currentTrackDuration = 0;
let serverCurrentTime = 0;
let lastUpdateTime = 0;

// Set initial volume
audio.volume = 0.7;

// ========================================
// AUTHENTICATION
// ========================================

async function performAuth(endpoint, data, submitBtn, messageDiv, onSuccess) {
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = endpoint === 'login' ? t('logging_in_text') : t('registering_text');
    messageDiv.innerHTML = '';
    
    try {
        const response = await fetch(`${API_URL}/auth/${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            if (endpoint === 'login') {
                authToken = result.token;
                currentUser = result.user;
                localStorage.setItem('authToken', authToken);
                localStorage.setItem('currentUser', JSON.stringify(currentUser));
                updateAuthUI();
            }
            
            const successMsg = endpoint === 'login' ? t('login_success') : t('register_success_full');
            messageDiv.innerHTML = `<div class="auth-success">${successMsg}</div>`;
            
            setTimeout(() => {
                messageDiv.innerHTML = '';
                onSuccess();
            }, 2000);
        } else {
            const errorMsg = endpoint === 'login' ? t('login_error') : t('register_error');
            messageDiv.innerHTML = `<div class="auth-error">${result.message || errorMsg}</div>`;
        }
    } catch (error) {
        console.error(`${endpoint} error:`, error);
        messageDiv.innerHTML = `<div class="auth-error">${t('connection_error')}</div>`;
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
}

async function checkAuthStatus() {
    const token = localStorage.getItem('authToken');
    const user = localStorage.getItem('currentUser');
    
    if (token && user) {
        try {
            const response = await fetch(`${API_URL}/auth/verify`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            
            if (response.ok) {
                authToken = token;
                currentUser = JSON.parse(user);
                updateAuthUI();
                return;
            }
        } catch (error) {
            console.error('Token verification failed:', error);
        }
    }
    
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
    updateAuthUI();
}

function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
    updateAuthUI();
    
    const settingsModal = document.getElementById('settingsModal');
    if (settingsModal.classList.contains('active')) {
        document.getElementById('settingsLoggedIn').style.display = 'none';
        document.getElementById('settingsAuth').style.display = 'block';
    }
}

function updateAuthUI() {
    const logoSubtitle = document.querySelector('.logo p');
    
    if (currentUser) {
        logoSubtitle.textContent = t('welcome_message').replace('{username}', currentUser.username);
        logoSubtitle.classList.add('welcome-message');
    } else {
        logoSubtitle.textContent = t('app_subtitle');
        logoSubtitle.classList.remove('welcome-message');
    }
    
    updateProtectedFeatures();
}

function updateProtectedFeatures() {
    const isLoggedIn = !!currentUser;
    document.querySelector('.upload-section').style.display = isLoggedIn ? '' : 'none';
    document.querySelector('.tracks-section').style.display = isLoggedIn ? '' : 'none';
}

async function authenticatedFetch(url, options = {}) {
    const headers = { ...options.headers };
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
    return fetch(url, { ...options, headers });
}

// ========================================
// MODAL MANAGEMENT
// ========================================

const modals = {
    auth: 'authModal',
    settings: 'settingsModal',
    tracks: 'tracksModal',
    changeCredentials: 'changeCredentialsModal',
    confirm: 'confirmOverlay'
};

function showModal(modalName, onShow) {
    const modalId = modals[modalName];
    if (onShow) onShow();
    document.getElementById(modalId).classList.add('active');
}

function hideModal(modalName, onHide) {
    const modalId = modals[modalName];
    const modal = document.getElementById(modalId);
    
    if (modal.classList.contains('active')) {
        modal.classList.add('closing');
        setTimeout(() => {
            modal.classList.remove('active', 'closing');
            if (onHide) onHide();
        }, 300);
    }
}

function showAuthModal() {
    showModal('auth', () => document.getElementById('loginUsername').focus());
}

function hideAuthModal() {
    hideModal('auth', () => {
        document.getElementById('loginForm').reset();
        document.getElementById('registerForm').reset();
        document.getElementById('loginMessage').innerHTML = '';
        document.getElementById('registerMessage').innerHTML = '';
    });
}

function showSettings() {
    showModal('settings', () => {
        fetch(`${API_URL}/`)
            .then(res => res.json())
            .then(data => {
                document.getElementById('radioName').textContent = data.name;
                document.getElementById('apiVersion').textContent = `v${data.version}`;
            })
            .catch(() => {
                document.getElementById('radioName').textContent = t('radio_name');
                document.getElementById('apiVersion').textContent = t('api_version');
            });
        
        const isLoggedIn = currentUser && authToken;
        document.getElementById('settingsLoggedIn').style.display = isLoggedIn ? 'block' : 'none';
        document.getElementById('settingsAuth').style.display = isLoggedIn ? 'none' : 'block';
    });
}

function hideSettingsModal() {
    hideModal('settings', () => {
        document.getElementById('settingsLoginForm').reset();
        document.getElementById('settingsRegisterForm').reset();
        document.getElementById('settingsLoginMessage').innerHTML = '';
        document.getElementById('settingsRegisterMessage').innerHTML = '';
    });
}

function showTracksModal() {
    showModal('tracks', () => loadTracksList());
}

function hideTracksModal() {
    hideModal('tracks');
}

function showChangeCredentials() {
    hideSettingsModal();
    showModal('changeCredentials', () => {
        document.getElementById('changeForm').reset();
        document.getElementById('changeMessage').innerHTML = '';
    });
}

function hideChangeCredentialsModal() {
    hideModal('changeCredentials');
}

function showConfirmDialog(title, message, type = 'confirm', showCancel = true) {
    return new Promise((resolve) => {
        confirmResolve = resolve;
        document.getElementById('confirmTitle').textContent = title;
        document.getElementById('confirmMessage').textContent = message;
        
        const confirmBtn = document.getElementById('confirmBtn');
        const cancelBtn = document.querySelector('.confirm-btn-cancel');
        
        const btnClasses = {
            warning: 'confirm-btn-warning',
            success: 'confirm-btn-success',
            confirm: 'confirm-btn-confirm'
        };
        
        confirmBtn.className = `confirm-btn ${btnClasses[type] || btnClasses.confirm}`;
        cancelBtn.style.display = showCancel ? 'block' : 'none';
        confirmBtn.textContent = showCancel ? t('confirm_button') : t('ok_button');
        
        document.getElementById('confirmOverlay').classList.add('active');
    });
}

function closeConfirmDialog(result) {
    const overlay = document.getElementById('confirmOverlay');
    if (overlay.classList.contains('active')) {
        overlay.classList.add('closing');
        setTimeout(() => {
            overlay.classList.remove('active', 'closing');
            if (confirmResolve) {
                confirmResolve(result);
                confirmResolve = null;
            }
        }, 300);
    }
}

function switchAuthTab(tab, isSettings = false) {
    const prefix = isSettings ? 'settings-auth-tab' : 'auth-tab';
    const loginTab = document.querySelector(`.${prefix}:nth-child(1)`);
    const registerTab = document.querySelector(`.${prefix}:nth-child(2)`);
    const loginForm = document.getElementById(isSettings ? 'settingsLoginForm' : 'loginForm');
    const registerForm = document.getElementById(isSettings ? 'settingsRegisterForm' : 'registerForm');
    
    const isLogin = tab === 'login';
    loginTab.classList.toggle('active', isLogin);
    registerTab.classList.toggle('active', !isLogin);
    loginForm.classList.toggle('active', isLogin);
    registerForm.classList.toggle('active', !isLogin);
    
    if (!isSettings) {
        const switchText = document.getElementById('authSwitchText');
        switchText.innerHTML = isLogin ? t('no_account') : t('have_account');
    }
}

function switchSettingsAuthTab(tab) {
    switchAuthTab(tab, true);
}

// ========================================
// FORM HANDLERS
// ========================================

async function handleLogin(event) {
    event.preventDefault();
    await performAuth('login', {
        username: document.getElementById('loginUsername').value,
        password: document.getElementById('loginPassword').value
    }, document.getElementById('loginSubmitBtn'), document.getElementById('loginMessage'), hideAuthModal);
}

async function handleRegister(event) {
    event.preventDefault();
    await performAuth('register', {
        username: document.getElementById('registerUsername').value,
        email: document.getElementById('registerEmail').value,
        password: document.getElementById('registerPassword').value
    }, document.getElementById('registerSubmitBtn'), document.getElementById('registerMessage'), () => switchAuthTab('login'));
}

async function handleSettingsLogin(event) {
    event.preventDefault();
    await performAuth('login', {
        username: document.getElementById('settingsLoginUsername').value,
        password: document.getElementById('settingsLoginPassword').value
    }, document.getElementById('settingsLoginSubmitBtn'), document.getElementById('settingsLoginMessage'), () => {
        document.getElementById('settingsLoggedIn').style.display = 'block';
        document.getElementById('settingsAuth').style.display = 'none';
    });
}

async function handleSettingsRegister(event) {
    event.preventDefault();
    await performAuth('register', {
        username: document.getElementById('settingsRegisterUsername').value,
        email: document.getElementById('settingsRegisterEmail').value,
        password: document.getElementById('settingsRegisterPassword').value
    }, document.getElementById('settingsRegisterSubmitBtn'), document.getElementById('settingsRegisterMessage'), () => switchSettingsAuthTab('login'));
}

async function handleChangeCredentials(event) {
    event.preventDefault();
    
    const newUsername = document.getElementById('newUsername').value.trim();
    const newEmail = document.getElementById('newEmail').value.trim();
    const newPassword = document.getElementById('newPassword').value;
    const submitBtn = document.getElementById('changeSubmitBtn');
    const messageDiv = document.getElementById('changeMessage');
    
    const updateData = {};
    if (newUsername) updateData.username = newUsername;
    if (newEmail) updateData.email = newEmail;
    if (newPassword) updateData.password = newPassword;
    
    if (Object.keys(updateData).length === 0) {
        messageDiv.innerHTML = `<div class="auth-error">${t('no_changes_error')}</div>`;
        return;
    }
    
    submitBtn.disabled = true;
    submitBtn.textContent = t('updating_text');
    messageDiv.innerHTML = '';
    
    try {
        const response = await authenticatedFetch(`${API_URL}/auth/profile`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updateData)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            if (data.user) {
                currentUser = data.user;
                localStorage.setItem('currentUser', JSON.stringify(currentUser));
                updateAuthUI();
            }
            if (data.token) {
                authToken = data.token;
                localStorage.setItem('authToken', authToken);
            }
            
            messageDiv.innerHTML = `<div class="auth-success">${t('credentials_updated')}</div>`;
            setTimeout(() => hideChangeCredentialsModal(), 2000);
        } else {
            messageDiv.innerHTML = `<div class="auth-error">${data.error || t('update_error')}</div>`;
        }
    } catch (error) {
        console.error('Change credentials error:', error);
        messageDiv.innerHTML = `<div class="auth-error">${t('connection_error')}</div>`;
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = t('update_button');
    }
}

// ========================================
// HLS STREAMING
// ========================================

function initHLS() {
    if (Hls.isSupported()) {
        hls = new Hls({
            maxBufferLength: 30,
            maxMaxBufferLength: 60,
            maxBufferSize: 60 * 1000 * 1000,
            maxBufferHole: 0.5,
            liveSyncDuration: 3,
            liveMaxLatencyDuration: 30,
            liveDurationInfinity: true,
            liveBackBufferLength: 0,
            manifestLoadingTimeOut: 5000,
            manifestLoadingMaxRetry: 15,
            manifestLoadingRetryDelay: 200,
            levelLoadingTimeOut: 5000,
            levelLoadingMaxRetry: 15,
            fragLoadingTimeOut: 10000,
            fragLoadingMaxRetry: 15,
            nudgeOffset: 0.1,
            nudgeMaxRetry: 15,
            enableWorker: true,
            enableSoftwareAES: true,
            startLevel: -1,
            autoStartLoad: true,
            testBandwidth: false,
            startFragPrefetch: true,
            lowLatencyMode: false,
            backBufferLength: 0,
            debug: false
        });
        
        hls.loadSource(`${API_URL}/playlist.m3u8`);
        hls.attachMedia(audio);
        
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
            console.log('✓ HLS manifest loaded');
            autoplayStream();
        });
        
        hls.on(Hls.Events.ERROR, (event, data) => {
            if (data.details === 'bufferStalledError') {
                console.log('⏳ Buffer stalled, waiting...');
                return;
            }
            
            if (data.fatal) {
                console.error('Fatal HLS error:', data);
                statusDiv.textContent = t('reconnecting');
                statusDiv.className = 'status buffering';
                
                switch(data.type) {
                    case Hls.ErrorTypes.NETWORK_ERROR:
                        hls.startLoad();
                        break;
                    case Hls.ErrorTypes.MEDIA_ERROR:
                        hls.recoverMediaError();
                        break;
                    default:
                        statusDiv.textContent = t('connection_error_status');
                        statusDiv.className = 'status';
                        setTimeout(() => {
                            if (isPlaying) {
                                hls.destroy();
                                initHLS();
                            }
                        }, 2000);
                        break;
                }
            }
        });
        
        hls.on(Hls.Events.FRAG_BUFFERED, (event, data) => {
            console.log('✓ Segment buffered:', data.frag.sn);
        });
        
        hls.on(Hls.Events.FRAG_LOADED, () => {
            if (isPlaying) {
                statusDiv.className = 'status live';
                statusDiv.innerHTML = `<span class="live-indicator"></span>${t('live_status')}`;
            }
        });
        
    } else if (audio.canPlayType('application/vnd.apple.mpegurl')) {
        audio.src = `${API_URL}/playlist.m3u8`;
        audio.addEventListener('loadedmetadata', autoplayStream);
    }
}

function autoplayStream() {
    statusDiv.className = 'status buffering';
    statusDiv.textContent = t('auto_starting');
    
    audio.play()
        .then(() => {
            isPlaying = true;
            playBtn.textContent = t('pause_button');
            playBtn.style.animation = 'none';
            statusDiv.className = 'status live';
            statusDiv.innerHTML = `<span class="live-indicator"></span>${t('live_status')}`;
            console.log('✓ Autoplay started');
            updateMetadata();
        })
        .catch(err => {
            console.warn('Autoplay blocked:', err);
            statusDiv.innerHTML = t('click_to_listen');
            statusDiv.className = 'status';
            playBtn.style.animation = 'pulse 2s infinite';
        });
}

function togglePlay() {
    isPlaying ? stopStream() : startStream();
}

function startStream() {
    if (!hls) {
        initHLS();
        setTimeout(() => attemptPlay(), 500);
    } else {
        attemptPlay();
    }
}

function attemptPlay() {
    statusDiv.className = 'status buffering';
    statusDiv.textContent = t('connecting');
    playBtn.style.animation = 'none';
    
    audio.play()
        .then(() => {
            isPlaying = true;
            playBtn.textContent = t('pause_button');
            updateMetadata();
        })
        .catch(err => {
            console.error('Play error:', err);
            statusDiv.textContent = t('error_prefix') + err.message;
            statusDiv.className = 'status';
            playBtn.style.animation = 'pulse 2s infinite';
        });
}

function stopStream() {
    audio.pause();
    isPlaying = false;
    playBtn.textContent = t('play_button');
    statusDiv.className = 'status';
    statusDiv.textContent = t('stream_stopped');
}

function setVolume(value) {
    audio.volume = value / 100;
}

// ========================================
// METADATA & PROGRESS
// ========================================

async function updateMetadata() {
    try {
        const response = await fetch(`${API_URL}/status`);
        const data = await response.json();
        
        if (data.metadata) {
            const newTitle = data.metadata.title || 'Unknown';
            const currentTitle = document.getElementById('track-title').textContent;
            
            if (newTitle !== currentTitle) {
                currentTrackDuration = data.metadata.duration || 0;
            }
            
            document.getElementById('track-title').textContent = newTitle;
            document.getElementById('track-artist').textContent = data.metadata.artist || 'Unknown';
            
            if (data.current_time !== undefined) {
                serverCurrentTime = data.current_time;
                lastUpdateTime = Date.now();
            }
        }
        
        const nextTrackDiv = document.getElementById('nextTrack');
        const nextTrackInfo = document.getElementById('next-track-info');
        if (data.next_track) {
            nextTrackDiv.style.display = 'block';
            nextTrackInfo.textContent = `${data.next_track.artist} - ${data.next_track.title}`;
        } else {
            nextTrackDiv.style.display = 'none';
        }
        
        const queueList = document.getElementById('queueList');
        if (data.queue && data.queue.length > 0) {
            queueList.innerHTML = data.queue.map((item, index) => {
                const artist = item.artist || t('unknown_artist');
                const title = item.title || 'Unknown';
                return `<div class="queue-item">${index + 1}. ${escapeHtml(artist)} - ${escapeHtml(title)}</div>`;
            }).join('');
        } else {
            queueList.innerHTML = `<div class="no-queue">${t('no_queue')}</div>`;
        }
        
        if (isPlaying) setTimeout(updateMetadata, 3000);
    } catch (err) {
        console.error('Metadata error:', err);
    }
}

function updateProgress() {
    if (isPlaying && currentTrackDuration > 0) {
        const timeSinceUpdate = (Date.now() - lastUpdateTime) / 1000;
        const currentTime = Math.min(serverCurrentTime + timeSinceUpdate, currentTrackDuration);
        const percentage = (currentTime / currentTrackDuration) * 100;
        document.getElementById('progressFill').style.width = `${percentage}%`;
    }
    requestAnimationFrame(updateProgress);
}

// ========================================
// FILE UPLOAD
// ========================================

function handleFileSelect(event) {
    selectedFile = event.target.files[0];
    const fileLabel = document.getElementById('fileLabel');
    const uploadBtn = document.getElementById('uploadBtn');
    
    if (selectedFile) {
        fileLabel.textContent = `📁 ${selectedFile.name}`;
        uploadBtn.disabled = false;
    } else {
        fileLabel.textContent = t('choose_file');
        uploadBtn.disabled = true;
    }
}

async function uploadFile() {
    if (!selectedFile) return;
    if (!currentUser) {
        showAuthModal();
        return;
    }
    
    const uploadBtn = document.getElementById('uploadBtn');
    const originalText = uploadBtn.textContent;
    
    try {
        uploadBtn.disabled = true;
        uploadBtn.textContent = '⏳ Caricamento...';
        
        const formData = new FormData();
        formData.append('file', selectedFile);
        
        const response = await authenticatedFetch(`${API_URL}/upload`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            uploadBtn.textContent = t('upload_success_button');
            document.getElementById('fileLabel').textContent = t('choose_file');
            document.getElementById('audioFile').value = '';
            selectedFile = null;
            
            updateMetadata();
            await loadTracksList();
            
            setTimeout(() => {
                uploadBtn.textContent = originalText;
                uploadBtn.disabled = true;
            }, 2000);
        } else {
            throw new Error(result.error || 'Upload failed');
        }
    } catch (err) {
        console.error('Upload error:', err);
        uploadBtn.textContent = t('upload_error_button');
        showConfirmDialog(t('error_title'), t('upload_error_generic').replace('{error}', err.message), 'confirm', false);
        
        setTimeout(() => {
            uploadBtn.textContent = originalText;
            uploadBtn.disabled = false;
        }, 2000);
    }
}

// ========================================
// TRACKS MANAGEMENT
// ========================================

async function loadTracksList() {
    try {
        const response = await fetch(`${API_URL}/tracks`);
        const data = await response.json();
        allTracks = (data.tracks || []).filter(track => 
            !track.filename || track.filename !== '_silence_placeholder.aac'
        );
        renderTracksList();
    } catch (err) {
        console.error('Tracks loading error:', err);
        const tracksList = document.getElementById('tracksList');
        if (tracksList) {
            tracksList.innerHTML = `<div class="loading" style="color: red;">${t('tracks_loading_error')}</div>`;
        }
    }
}

function renderTracksList() {
    const tracksList = document.getElementById('tracksList');
    
    if (allTracks.length === 0) {
        tracksList.innerHTML = `<div class="loading">${t('no_tracks_available')}</div>`;
        return;
    }

    tracksList.innerHTML = allTracks.map((track, index) => {
        const duration = formatDuration(track.duration);
        return `
            <div class="track-item">
                <div class="track-info">
                    <div class="track-title">${escapeHtml(track.title || track.filename)}</div>
                    <div class="track-artist">${escapeHtml(track.artist || t('unknown_artist'))}</div>
                    <div class="track-duration">${duration}</div>
                </div>
                <div class="track-actions">
                    <button class="add-track-btn" 
                            onclick="addTrackToQueue(${index})"
                            ${track.in_queue ? 'disabled' : ''}>
                        ${track.in_queue ? t('already_in_queue') : t('add_to_queue')}
                    </button>
                    ${track.in_queue ? `
                    <button class="remove-queue-btn" 
                            onclick="removeFromQueue(${index})"
                            title="${t('remove_from_queue_tooltip')}">
                        ${t('remove_from_queue')}
                    </button>` : ''}
                    <button class="remove-track-btn" 
                            onclick="removeTrack(${index})"
                            title="${t('delete_track_tooltip')}">
                        ${t('delete_track')}
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

async function addTrackToQueue(trackIndex) {
    if (!currentUser) {
        showAuthModal();
        return;
    }
    
    if (trackIndex < 0 || trackIndex >= allTracks.length) {
        showConfirmDialog(t('error_title'), 'Brano non valido', 'confirm', false);
        return;
    }
    
    const track = allTracks[trackIndex];
    
    try {
        const response = await authenticatedFetch(`${API_URL}/queue/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filepath: track.filepath })
        });

        const result = await response.json();

        if (result.success) {
            track.in_queue = true;
            renderTracksList();
            setTimeout(() => loadTracksList(), 5000);
            updateMetadata();
            
            const meta = result.metadata;
            showConfirmDialog(t('success_title'), 
                t('track_added_to_queue').replace('{artist}', meta.artist).replace('{title}', meta.title), 
                'success', false);
        } else {
            throw new Error(result.error || 'Errore aggiunta alla coda');
        }
    } catch (err) {
        console.error('Queue add error:', err);
        showConfirmDialog(t('error_title'), t('queue_add_error').replace('{error}', err.message), 'confirm', false);
    }
}

async function removeTrack(trackIndex) {
    if (!currentUser) {
        showAuthModal();
        return;
    }
    
    if (trackIndex < 0 || trackIndex >= allTracks.length) {
        showConfirmDialog(t('error_title'), t('invalid_track_error'), 'confirm', false);
        return;
    }
    
    const track = allTracks[trackIndex];
    const trackName = `${track.artist} - ${track.title}`;
    
    const confirmed = await showConfirmDialog(
        t('confirm_delete_track_title'),
        t('confirm_delete_track_message').replace('{track}', trackName),
        'confirm'
    );
    
    if (!confirmed) return;
    
    try {
        const response = await authenticatedFetch(`${API_URL}/track/remove`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filepath: track.filepath })
        });

        const result = await response.json();

        if (result.success) {
            allTracks.splice(trackIndex, 1);
            renderTracksList();
            setTimeout(() => loadTracksList(), 5000);
            updateMetadata();
            
            await showConfirmDialog(
                t('delete_success_title'),
                t('delete_success_message').replace('{track}', trackName),
                'confirm', false
            );
        } else {
            await showConfirmDialog(
                t('delete_error_title'),
                result.message || t('delete_error_message'),
                'warning', false
            );
        }
    } catch (err) {
        console.error('Track removal error:', err);
        await showConfirmDialog(
            t('connection_error_title'),
            t('connection_error_message').replace('{message}', err.message),
            'warning', false
        );
    }
}

async function removeFromQueue(trackIndex) {
    if (!currentUser) {
        showAuthModal();
        return;
    }
    
    if (trackIndex < 0 || trackIndex >= allTracks.length) {
        showConfirmDialog(t('error_title'), t('invalid_track_error'), 'confirm', false);
        return;
    }
    
    const track = allTracks[trackIndex];
    const trackName = `${track.artist} - ${track.title}`;
    
    const confirmed = await showConfirmDialog(
        t('confirm_remove_from_queue_title'),
        t('confirm_remove_from_queue_message').replace('{track}', trackName),
        'warning'
    );
    
    if (!confirmed) return;
    
    try {
        const response = await authenticatedFetch(`${API_URL}/queue/remove`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filepath: track.filepath })
        });

        const result = await response.json();

        if (result.success) {
            track.in_queue = false;
            renderTracksList();
            setTimeout(() => loadTracksList(), 5000);
            updateMetadata();
            
            showConfirmDialog(t('success_title'), `${trackName} rimosso dalla coda`, 'success', false);
        } else {
            throw new Error(result.message || 'Errore rimozione dalla coda');
        }
    } catch (err) {
        console.error('Queue removal error:', err);
        showConfirmDialog(t('error_title'), t('queue_add_error').replace('{error}', err.message), 'confirm', false);
    }
}

// ========================================
// UTILITIES
// ========================================

function formatDuration(seconds) {
    if (!seconds || seconds === 0) return '-';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ========================================
// EVENT LISTENERS
// ========================================

audio.addEventListener('waiting', () => {
    if (isPlaying) {
        statusDiv.className = 'status buffering';
        statusDiv.textContent = '⏳ Buffering...';
    }
});

audio.addEventListener('playing', () => {
    if (isPlaying) {
        statusDiv.className = 'status live';
        statusDiv.innerHTML = `<span class="live-indicator"></span>${t('live_status')}`;
    }
});

audio.addEventListener('error', (e) => {
    console.error('Audio error:', e);
    statusDiv.textContent = t('playback_error');
    statusDiv.className = 'status';
});

document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
        const modalsToCheck = [
            { id: 'authModal', hide: hideAuthModal },
            { id: 'settingsModal', hide: hideSettingsModal },
            { id: 'tracksModal', hide: hideTracksModal },
            { id: 'changeCredentialsModal', hide: hideChangeCredentialsModal },
            { id: 'confirmOverlay', hide: () => closeConfirmDialog(false) }
        ];
        
        for (const modal of modalsToCheck) {
            if (document.getElementById(modal.id).classList.contains('active')) {
                modal.hide();
                return;
            }
        }
    }
});

// ========================================
// INITIALIZATION
// ========================================

window.addEventListener('DOMContentLoaded', () => {
    console.log('🎵 Initializing radio...');
    initHLS();
    loadTracksList();
    checkAuthStatus();
});

// Start metadata updates
updateMetadata();
updateProgress();

// Update queue periodically (avoid when modals are open)
setInterval(() => {
    const hasOpenModal = document.querySelector('.auth-modal.active, .settings-modal.active, .change-credentials-modal.active, .confirm-overlay.active');
    if (!hasOpenModal) {
        updateMetadata();
    }
}, 5000);