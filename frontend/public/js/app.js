const API_URL = window.API_URL || 'http://localhost:5001';
const audio = document.getElementById('audio');
const playBtn = document.getElementById('playBtn');
const statusDiv = document.getElementById('status');

let isPlaying = false;
let hls = null;
let currentUser = null;
let authToken = null;

// === COMMON AUTH FUNCTIONS ===
async function performLogin(usernameId, passwordId, submitBtnId, messageDivId, onSuccess) {
    const username = document.getElementById(usernameId).value;
    const password = document.getElementById(passwordId).value;
    const submitBtn = document.getElementById(submitBtnId);
    const messageDiv = document.getElementById(messageDivId);
    
    submitBtn.disabled = true;
    submitBtn.textContent = t('logging_in_text');
    messageDiv.innerHTML = '';
    
    try {
        const response = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            authToken = data.token;
            currentUser = data.user;
            
            // Save to localStorage
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('currentUser', JSON.stringify(currentUser));
            
            updateAuthUI();
            onSuccess();
            
            messageDiv.innerHTML = `<div class="auth-success">${t('login_success')}</div>`;
            setTimeout(() => {
                messageDiv.innerHTML = '';
            }, 2000);
        } else {
            messageDiv.innerHTML = `<div class="auth-error">${data.message || t('login_error')}</div>`;
        }
    } catch (error) {
        console.error('Login error:', error);
        messageDiv.innerHTML = `<div class="auth-error">${t('connection_error')}</div>`;
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = t('login_button_text');
    }
}

async function performRegister(usernameId, emailId, passwordId, submitBtnId, messageDivId, onSuccess) {
    const username = document.getElementById(usernameId).value;
    const email = document.getElementById(emailId).value;
    const password = document.getElementById(passwordId).value;
    const submitBtn = document.getElementById(submitBtnId);
    const messageDiv = document.getElementById(messageDivId);
    
    submitBtn.disabled = true;
    submitBtn.textContent = t('registering_text');
    messageDiv.innerHTML = '';
    
    try {
        const response = await fetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, email, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            onSuccess();
            messageDiv.innerHTML = `<div class="auth-success">${t('register_success_full')}</div>`;
            setTimeout(() => {
                messageDiv.innerHTML = '';
            }, 2000);
        } else {
            messageDiv.innerHTML = `<div class="auth-error">${data.message || t('register_error')}</div>`;
        }
    } catch (error) {
        console.error('Register error:', error);
        messageDiv.innerHTML = `<div class="auth-error">${t('connection_error')}</div>`;
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = t('register_button_text');
    }
}

// === CUSTOM CONFIRM DIALOG ===
let confirmResolve = null;

function showConfirmDialog(title, message, type = 'confirm', showCancel = true) {
    return new Promise((resolve) => {
        confirmResolve = resolve;
        document.getElementById('confirmTitle').textContent = title;
        document.getElementById('confirmMessage').textContent = message;
        document.getElementById('confirmOverlay').classList.add('active');
        
        const confirmBtn = document.getElementById('confirmBtn');
        const cancelBtn = document.querySelector('.confirm-btn-cancel');
        
        // Set the confirm button style
        let btnClass = 'confirm-btn-confirm';
        if (type === 'warning') {
            btnClass = 'confirm-btn-warning';
        } else if (type === 'success') {
            btnClass = 'confirm-btn-success';
        }
        confirmBtn.className = 'confirm-btn ' + btnClass;
        
        // Show/hide the Cancel button
        if (showCancel) {
            cancelBtn.style.display = 'block';
            confirmBtn.textContent = t('confirm_button');
        } else {
            cancelBtn.style.display = 'none';
            confirmBtn.textContent = t('ok_button');
        }
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

function showSettings() {
    // Load radio info
    fetch(`${API_URL}/`)
        .then(response => response.json())
        .then(data => {
            document.getElementById('radioName').textContent = data.name;
            document.getElementById('apiVersion').textContent = `v${data.version}`;
        })
        .catch(error => {
            console.error('Error loading radio info:', error);
            document.getElementById('radioName').textContent = t('radio_name');
            document.getElementById('apiVersion').textContent = t('api_version');
        });

    // Show appropriate sections based on login status
    const loggedInSection = document.getElementById('settingsLoggedIn');
    const authSection = document.getElementById('settingsAuth');
    
    if (currentUser && authToken) {
        loggedInSection.style.display = 'block';
        authSection.style.display = 'none';
    } else {
        loggedInSection.style.display = 'none';
        authSection.style.display = 'block';
    }

    document.getElementById('settingsModal').classList.add('active');
}

function hideSettingsModal() {
    const modal = document.getElementById('settingsModal');
    if (modal.classList.contains('active')) {
        modal.classList.add('closing');
        setTimeout(() => {
            modal.classList.remove('active', 'closing');
            // Reset auth forms
            document.getElementById('settingsLoginForm').reset();
            document.getElementById('settingsRegisterForm').reset();
            document.getElementById('settingsLoginMessage').innerHTML = '';
            document.getElementById('settingsRegisterMessage').innerHTML = '';
        }, 300);
    }
}

function showTracksModal() {
    // Always load fresh tracks when opening modal
    loadTracksList();
    
    document.getElementById('tracksModal').classList.add('active');
}

function hideTracksModal() {
    const modal = document.getElementById('tracksModal');
    if (modal.classList.contains('active')) {
        modal.classList.add('closing');
        setTimeout(() => {
            modal.classList.remove('active', 'closing');
        }, 300);
    }
}

function switchSettingsAuthTab(tab) {
    const loginTab = document.querySelector('.settings-auth-tab:nth-child(1)');
    const registerTab = document.querySelector('.settings-auth-tab:nth-child(2)');
    const loginForm = document.getElementById('settingsLoginForm');
    const registerForm = document.getElementById('settingsRegisterForm');

    if (tab === 'login') {
        loginTab.classList.add('active');
        registerTab.classList.remove('active');
        loginForm.classList.add('active');
        registerForm.classList.remove('active');
    } else {
        registerTab.classList.add('active');
        loginTab.classList.remove('active');
        registerForm.classList.add('active');
        loginForm.classList.remove('active');
    }
}

async function handleSettingsLogin(event) {
    event.preventDefault();
    await performLogin('settingsLoginUsername', 'settingsLoginPassword', 'settingsLoginSubmitBtn', 'settingsLoginMessage', () => {
        // Update settings modal to show account section
        document.getElementById('settingsLoggedIn').style.display = 'block';
        document.getElementById('settingsAuth').style.display = 'none';
    });
}

async function handleSettingsRegister(event) {
    event.preventDefault();
    await performRegister('settingsRegisterUsername', 'settingsRegisterEmail', 'settingsRegisterPassword', 'settingsRegisterSubmitBtn', 'settingsRegisterMessage', () => {
        switchSettingsAuthTab('login');
    });
}

function showChangeCredentials() {
    hideSettingsModal();
    document.getElementById('changeCredentialsModal').classList.add('active');
    document.getElementById('changeForm').reset();
    document.getElementById('changeMessage').innerHTML = '';
}

function hideChangeCredentialsModal() {
    const modal = document.getElementById('changeCredentialsModal');
    if (modal.classList.contains('active')) {
        modal.classList.add('closing');
        setTimeout(() => {
            modal.classList.remove('active', 'closing');
        }, 300);
    }
}

// === AUTHENTICATION FUNCTIONS ===

function showAuthModal() {
    document.getElementById('authModal').classList.add('active');
    document.getElementById('loginUsername').focus();
}

function hideAuthModal() {
    const modal = document.getElementById('authModal');
    if (modal.classList.contains('active')) {
        modal.classList.add('closing');
        setTimeout(() => {
            modal.classList.remove('active', 'closing');
            // Reset forms
            document.getElementById('loginForm').reset();
            document.getElementById('registerForm').reset();
            document.getElementById('loginMessage').innerHTML = '';
            document.getElementById('registerMessage').innerHTML = '';
        }, 300);
    }
}

function switchAuthTab(tab) {
    const loginTab = document.querySelector('.auth-tab:nth-child(1)');
    const registerTab = document.querySelector('.auth-tab:nth-child(2)');
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const switchText = document.getElementById('authSwitchText');

    if (tab === 'login') {
        loginTab.classList.add('active');
        registerTab.classList.remove('active');
        loginForm.classList.add('active');
        registerForm.classList.remove('active');
        switchText.innerHTML = t('no_account');
    } else {
        registerTab.classList.add('active');
        loginTab.classList.remove('active');
        registerForm.classList.add('active');
        loginForm.classList.remove('active');
        switchText.innerHTML = t('have_account');
    }
}

async function handleLogin(event) {
    event.preventDefault();
    await performLogin('loginUsername', 'loginPassword', 'loginSubmitBtn', 'loginMessage', () => {
        hideAuthModal();
    });
}

async function handleRegister(event) {
    event.preventDefault();
    await performRegister('registerUsername', 'registerEmail', 'registerPassword', 'registerSubmitBtn', 'registerMessage', () => {
        switchAuthTab('login');
    });
}

async function handleChangeCredentials(event) {
    event.preventDefault();
    
    const newUsername = document.getElementById('newUsername').value.trim();
    const newEmail = document.getElementById('newEmail').value.trim();
    const newPassword = document.getElementById('newPassword').value;
    const submitBtn = document.getElementById('changeSubmitBtn');
    const messageDiv = document.getElementById('changeMessage');
    
    submitBtn.disabled = true;
    submitBtn.textContent = t('updating_text');
    messageDiv.innerHTML = '';
    
    // Prepare update data
    const updateData = {};
    if (newUsername) updateData.username = newUsername;
    if (newEmail) updateData.email = newEmail;
    if (newPassword) updateData.password = newPassword;
    
    // Check if at least one field is provided
    if (Object.keys(updateData).length === 0) {
        messageDiv.innerHTML = `<div class="auth-error">${t('no_changes_error')}</div>`;
        submitBtn.disabled = false;
        submitBtn.textContent = t('update_button');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/auth/profile`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify(updateData)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Update current user info if username changed
            if (data.user) {
                currentUser = data.user;
                localStorage.setItem('currentUser', JSON.stringify(currentUser));
                updateAuthUI();
            }
            
            // Update token if provided
            if (data.token) {
                authToken = data.token;
                localStorage.setItem('authToken', authToken);
            }
            
            messageDiv.innerHTML = `<div class="auth-success">${t('credentials_updated')}</div>`;
            setTimeout(() => {
                hideChangeCredentialsModal();
            }, 2000);
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

function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
    updateAuthUI();
    
    // If settings modal is open, update it to show auth section
    const settingsModal = document.getElementById('settingsModal');
    if (settingsModal.classList.contains('active')) {
        document.getElementById('settingsLoggedIn').style.display = 'none';
        document.getElementById('settingsAuth').style.display = 'block';
    }
}

function updateAuthUI() {
    const logoSubtitle = document.querySelector('.logo p');
    
    if (currentUser) {
        // Show username instead of "HLS Live Streaming"
        logoSubtitle.textContent = t('welcome_message').replace('{username}', currentUser.username);
        logoSubtitle.classList.add('welcome-message');
    } else {
        // Restore original text when not logged in
        logoSubtitle.textContent = t('app_subtitle');
        logoSubtitle.classList.remove('welcome-message');
    }
    
    // Update protected features
    updateProtectedFeatures();
}

function updateProtectedFeatures() {
    const isLoggedIn = !!currentUser;
    const uploadSection = document.querySelector('.upload-section');
    const tracksSection = document.querySelector('.tracks-section');
    
    if (isLoggedIn) {
        uploadSection.style.display = '';
        tracksSection.style.display = '';
    } else {
        uploadSection.style.display = 'none';
        tracksSection.style.display = 'none';
    }
}

async function checkAuthStatus() {
    const token = localStorage.getItem('authToken');
    const user = localStorage.getItem('currentUser');
    
    if (token && user) {
        try {
            // Verify token with server
            const response = await fetch(`${API_URL}/auth/verify`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                authToken = token;
                currentUser = JSON.parse(user);
                updateAuthUI();
                return;
            }
        } catch (error) {
            console.error('Token verification failed:', error);
        }
    }
    
    // Clear invalid auth data
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
    updateAuthUI();
}

// Helper function for authenticated requests
async function authenticatedFetch(url, options = {}) {
    const headers = { ...options.headers };
    
    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }
    
    return fetch(url, {
        ...options,
        headers
    });
}

// Imposta volume iniziale
audio.volume = 0.7;

function initHLS() {
    if (Hls.isSupported()) {
        hls = new Hls({
            
            maxBufferLength: 30,
            maxMaxBufferLength: 60,
            maxBufferSize: 60 * 1000 * 1000,
            maxBufferHole: 0.5,
            startFragPrefetch: true,

            liveSyncDuration: 2,
            liveMaxLatencyDuration: 15,
            liveDurationInfinity: true,
            liveBackBufferLength: 0,
            
            manifestLoadingTimeOut: 5000,
            manifestLoadingMaxRetry: 15,
            manifestLoadingRetryDelay: 200,
            levelLoadingTimeOut: 5000,
            levelLoadingMaxRetry: 15,
            fragLoadingTimeOut: 10000,
            fragLoadingMaxRetry: 15,
            
            maxBufferHole: 0.1,
            nudgeOffset: 0.1,
            nudgeMaxRetry: 15,
            
            // Worker
            enableWorker: true,
            enableSoftwareAES: true,
            
            // Start
            startLevel: -1,
            autoStartLoad: true,
            testBandwidth: false,
            
            // Buffer management
            lowLatencyMode: false,
            backBufferLength: 0,
            
            // Debugging
            debug: false
        });
        
        hls.loadSource(`${API_URL}/playlist.m3u8`);
        hls.attachMedia(audio);
        
        hls.on(Hls.Events.MANIFEST_PARSED, function() {
            console.log('HLS manifest parsed, ready to play');
            autoplayStream();
        });
        
        hls.on(Hls.Events.ERROR, function(event, data) {
            console.warn('HLS Event:', data.type, data.details);
            
            if (data.details === 'bufferStalledError') {
                console.log('Buffer stalled, waiting for more data...');
                return;
            }
            
            if (data.fatal) {
                console.error('Fatal HLS error:', data);

                switch(data.type) {
                    case Hls.ErrorTypes.NETWORK_ERROR:
                        console.log('Network error, attempting recovery...');
                        statusDiv.textContent = t('reconnecting');
                        statusDiv.className = 'status buffering';
                        hls.startLoad();
                        break;
                    case Hls.ErrorTypes.MEDIA_ERROR:
                        console.log('Media error, attempting recovery...');
                        hls.recoverMediaError();
                        break;
                    default:
                        console.log('Irrecoverable error');
                        statusDiv.textContent = t('connection_error_status');
                        statusDiv.className = 'status';
                        // Prova a ricreare tutto
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
        
        // Log quando il buffer è pronto
        hls.on(Hls.Events.FRAG_BUFFERED, function(event, data) {
            console.log('Fragment buffered:', data.frag.sn);
        });
        
        hls.on(Hls.Events.FRAG_LOADED, function() {
            if (isPlaying) {
                statusDiv.className = 'status live';
                statusDiv.innerHTML = `<span class="live-indicator"></span>${t('live_status')}`;
            }
        });
        
    } else if (audio.canPlayType('application/vnd.apple.mpegurl')) {
        audio.src = `${API_URL}/playlist.m3u8`;
        audio.addEventListener('loadedmetadata', function() {
            autoplayStream();
        });
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
            console.log('Starting autoplay');
            updateMetadata();
        })
        .catch(err => {
            console.warn('Autoplay is disabled by browser:', err);
            statusDiv.innerHTML = t('click_to_listen');
            statusDiv.className = 'status';
            playBtn.style.animation = 'pulse 2s infinite'; 
        });
}

function togglePlay() {
    if (!isPlaying) {
        startStream();
    } else {
        stopStream();
    }
}

function startStream() {
    if (!hls) {
        initHLS();
        setTimeout(() => {
            attemptPlay();
        }, 500);
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
            console.error('Errore play:', err);
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

// Track progress data
let currentTrackDuration = 0;
let serverCurrentTime = 0;
let lastUpdateTime = 0;  

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
        
        // Next track
        const nextTrackDiv = document.getElementById('nextTrack');
        const nextTrackInfo = document.getElementById('next-track-info');
        if (data.next_track) {
            nextTrackDiv.style.display = 'block';
            const nextText = `${data.next_track.artist} - ${data.next_track.title}`;
            nextTrackInfo.textContent = nextText;
        } else {
            nextTrackDiv.style.display = 'none';
        }
        
        // Update queue
        const queueList = document.getElementById('queueList');
        if (data.queue && data.queue.length > 0) {
            queueList.innerHTML = data.queue.map((queueItem, index) => {
                const artist = queueItem.artist || t('unknown_artist');
                const title = queueItem.title || 'Unknown';
                return `<div class="queue-item">${index + 1}. ${escapeHtml(artist)} - ${escapeHtml(title)}</div>`;
            }).join('');
        } else {
            queueList.innerHTML = `<div class="no-queue">${t('no_queue')}</div>`;
        }
        
        if (isPlaying) {
            setTimeout(updateMetadata, 3000);
        }
    } catch (err) {
        console.error('Errore metadata:', err);
    }
}

// Progress bar update
function updateProgress() {
    if (isPlaying && currentTrackDuration > 0) {
        const timeSinceUpdate = (Date.now() - lastUpdateTime) / 1000;
        const currentTime = Math.min(serverCurrentTime + timeSinceUpdate, currentTrackDuration);
        const percentage = (currentTime / currentTrackDuration) * 100;
        
        document.getElementById('progressFill').style.width = `${percentage}%`;
    }
    requestAnimationFrame(updateProgress);
}

// Continuously update
updateProgress();

// File upload handling
let selectedFile = null;

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
        uploadBtn.textContent = 'Uploading...';
        
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
            throw new Error(result.error || 'Failed to upload');
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

// Event listeners per debug
audio.addEventListener('waiting', () => {
    if (isPlaying) {
        statusDiv.className = 'status buffering';
        statusDiv.textContent = 'Buffering...';
    }
});

audio.addEventListener('playing', () => {
    if (isPlaying) {
        statusDiv.className = 'status live';
        statusDiv.innerHTML = `<span class="live-indicator"></span>${t('live_status')}`;
    }
});

audio.addEventListener('error', (e) => {
    console.error('Errore audio:', e);
    statusDiv.textContent = t('playback_error');
    statusDiv.className = 'status';
});

window.addEventListener('DOMContentLoaded', function() {
    console.log('🎵 Radio initialization...');
    initHLS();
    loadTracksList();
});

updateMetadata();
setInterval(() => {
    const hasOpenModal = document.querySelector('.auth-modal.active, .settings-modal.active, .change-credentials-modal.active, .confirm-overlay.active');
    if (!hasOpenModal) {
        updateMetadata();
    }
}, 5000);  // Update every 5 seconds

// Tracks list management
let allTracks = [];

// Load tracks when modal is opened
async function loadTracksList() {
    try {
        const response = await fetch(`${API_URL}/tracks`);
        const data = await response.json();
        allTracks = (data.tracks || []).filter(track => 
            !track.filename || track.filename !== '_silence_placeholder.aac'
        );
        renderTracksList();
    } catch (err) {
        console.error('Error loading tracks:', err);
        const tracksList = document.getElementById('tracksList');
        if (tracksList) {
            tracksList.innerHTML = 
                `<div class="loading" style="color: red;">${t('tracks_loading_error')}</div>`;
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
        const inQueueBadge = '';
        
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
                    </button>
                    ` : ''}
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
    const filepath = track.filepath;
    
    try {
        const response = await authenticatedFetch(`${API_URL}/queue/add`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ filepath: filepath })
        });

        const result = await response.json();

        if (result.success) {
            // Updates infos
            track.in_queue = true;
            renderTracksList();
            setTimeout(() => loadTracksList(), 5000);
            updateMetadata();
            const meta = result.metadata;
            showConfirmDialog(t('success_title'), t('track_added_to_queue').replace('{artist}', meta.artist).replace('{title}', meta.title), 'success', false);
        } else {
            throw new Error(result.error || 'Failed to add to queue');
        }
    } catch (err) {
        console.error('Error adding to queue:', err);
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
    
    if (!confirmed) {
        return;
    }
    
    const filepath = track.filepath;
    
    try {
        const response = await authenticatedFetch(`${API_URL}/track/remove`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ filepath: filepath })
        });

        const result = await response.json();

        if (result.success) {
            // Remove track from local list for instant update
            allTracks.splice(trackIndex, 1);
            renderTracksList();
            setTimeout(() => loadTracksList(), 5000);
            updateMetadata();
            
            await showConfirmDialog(
                t('delete_success_title'),
                t('delete_success_message').replace('{track}', trackName),
                'confirm',
                false 
            );
        } else {
            await showConfirmDialog(
                t('delete_error_title'),
                result.message || t('delete_error_message'),
                'warning',
                false  
            );
        }
    } catch (err) {
        console.error('Error removing track:', err);
        await showConfirmDialog(
            t('connection_error_title'),
            t('connection_error_message').replace('{message}', err.message),
            'warning',
            false
        );
    }
}

async function removeFromQueue(trackIndex) {
    // Auth check
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
    
    if (!confirmed) {
        return;
    }
    
    const filepath = track.filepath;
    
    try {
        const response = await authenticatedFetch(`${API_URL}/queue/remove`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ filepath: filepath })
        });

        const result = await response.json();

        if (result.success) {
            // Update local track info
            track.in_queue = false;
            renderTracksList();
            setTimeout(() => loadTracksList(), 5000);
            updateMetadata();
            showConfirmDialog(t('success_title'), `${trackName} removed from queue`, 'success', false);
        } else {
            throw new Error(result.message || 'Error removing from queue');
        }
    } catch (err) {
        console.error('Error removing from queue:', err);
        showConfirmDialog(t('error_title'), t('queue_add_error').replace('{error}', err.message), 'confirm', false);
    }
}

function formatDuration(seconds) {
    if (!seconds || seconds === 0) return '-';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// === ESC KEY HANDLER ===
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        // Close auth modal if open
        const authModal = document.getElementById('authModal');
        if (authModal.classList.contains('active')) {
            hideAuthModal();
            return;
        }
        
        // Close settings modal if open
        const settingsModal = document.getElementById('settingsModal');
        if (settingsModal.classList.contains('active')) {
            hideSettingsModal();
            return;
        }
        
        // Close tracks modal if open
        const tracksModal = document.getElementById('tracksModal');
        if (tracksModal.classList.contains('active')) {
            hideTracksModal();
            return;
        }
        
        // Close change credentials modal if open
        const changeCredentialsModal = document.getElementById('changeCredentialsModal');
        if (changeCredentialsModal.classList.contains('active')) {
            hideChangeCredentialsModal();
            return;
        }
        
        // Close confirm dialog if open
        const confirmOverlay = document.getElementById('confirmOverlay');
        if (confirmOverlay.classList.contains('active')) {
            closeConfirmDialog(false);
            return;
        }
    }
});

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize authentication on page load
checkAuthStatus();