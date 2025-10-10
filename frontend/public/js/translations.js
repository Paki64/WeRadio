const translations = {
    // Titles and headers
    "app_title": "WeRadio",
    "app_subtitle": "HLS Live Streaming",
    "now_playing": "Loading...",
    "next_track": "⏭️ Next track:",
    "volume_label": "🔊 Volume",
    "upload_section_title": "🎵 Upload a Track",
    "tracks_section_title": "🎵 Music Library",
    "queue_section_title": "📋 Playback Queue",
    "tracks_modal_title": "🎵 Music Library",

    // Buttons
    "settings_button": "⚙️",
    "play_button": "▶️ LISTEN LIVE",
    "upload_button": "⬆️ Upload new track",
    "show_tracks_button": "Show",
    "close_button": "Close",
    "confirm_button": "Confirm",
    "ok_button": "OK",
    "cancel_button": "Cancel",
    "add_track_button": "➕ Add",
    "remove_from_queue_button": "➖ From queue",
    "delete_track_button": "🗑️ Delete",

    // Status and messages
    "loading": "Loading...",
    "loading_tracks": "Loading tracks...",
    "loading_queue": "Loading queue...",
    "click_to_start": "👇 Click to start listening",
    "no_tracks_available": "No tracks available",
    "no_queue": "No tracks in queue",
    "unknown_artist": "Unknown",
    "in_queue": "In queue",
    "already_in_queue": "✓ In queue",
    "add_to_queue": "➕ Add",
    "remove_from_queue": "➖ From queue",
    "delete_track": "🗑️ Delete",
    "remove_from_queue_tooltip": "Remove from queue",
    "delete_track_tooltip": "Delete track permanently",
    "tracks_loading_error": "Error loading tracks",
    "queue_title": "📋 Playback queue:",
    "track_in_queue": "In queue",

    // File input
    "choose_file": "📁 Choose an audio file",

    // Modal titles
    "settings_title": "Settings",
    "auth_title": "Authentication",
    "confirm_title": "Confirm",
    "error_title": "Error",
    "success_title": "Success",

    // Tabs and authentication sections
    "login_tab": "Login",
    "register_tab": "Registration",

    // Form labels
    "username_label": "Username",
    "password_label": "Password",
    "email_label": "Email",
    "confirm_password_label": "Confirm Password",
    "new_username_label": "New Username",
    "new_email_label": "New Email",
    "new_password_label": "New Password",

    // Placeholders
    "username_placeholder": "Enter username",
    "password_placeholder": "Enter password",
    "email_placeholder": "Enter email",
    "leave_empty_placeholder": "Leave empty to not change",

    // Buttons
    "login_button_text": "Login",
    "register_button_text": "Register",
    "save_profile_button": "💾 Save Profile",
    "change_credentials_button": "Change Credentials",
    "cancel_button": "Cancel",

    // Modal titles
    "change_credentials_title": "Change Credentials",

    // Messages
    "login_required": "Login required for this feature",

    // Error/success messages
    "login_success": "Login successful!",
    "register_success": "Registration completed!",
    "upload_success": "Track uploaded successfully!",
    "delete_success": "Track deleted successfully!",
    "generic_error": "An error occurred",
    "connection_error": "Connection error",
    "login_error": "Error during login",
    "register_success_full": "Registration completed! You can now log in.",
    "register_error": "Error during registration",

    // Button states
    "registering_text": "Registering...",
    "logging_in_text": "Logging in...",
    "updating_text": "Updating...",
    "uploading_text": "Uploading...",

    // Notification messages
    "track_added_to_queue": "✅ Added to queue!\n\n{artist} - {title}\n",
    "queue_add_error": "❌ Error: {error}",
    "track_removed_from_queue": "✅ {message}\n\n{trackName} removed from queue",
    "invalid_track_error": "❌ Error: Invalid track",
    "upload_error_generic": "❌ Error: {error}",
    "track_deleted_success": "✅ Track deleted successfully!",
    "confirm_delete_track": "Are you sure you want to permanently delete this track?",

    // Tooltips
    "settings_tooltip": "Settings",

    // Confirmations
    "confirm_logout": "Are you sure you want to log out?",

    // Settings sections
    "account_section": "Account",
    "logout_button": "Logout",

    // App info
    "radio_name": "WeRadio",
    "api_version": "v0.4",

    // Messages
    "login_required": "Login required for this feature",
    "insufficient_permissions": "Insufficient permissions",
    "welcome_message": "Welcome, {username}!",
    "credentials_updated": "Credentials updated successfully!",
    "update_error": "Error during update",
    "connection_error": "Connection error",
    "live_status": "LIVE",
    "click_to_listen": "👆 <strong>Click \"LISTEN LIVE\"</strong> to start",
    "no_account": "Don't have an account? <a onclick=\"switchAuthTab('register')\">Register</a>",
    "have_account": "Already have an account? <a onclick=\"switchAuthTab('login')\">Login</a>",
    "updating_text": "Updating...",
    "update_button": "Update",
    "reconnecting": "⚠️ Reconnecting...",
    "connection_error_status": "Connection error",
    "auto_starting": "⏳ Auto-starting...",
    "pause_button": "⏸️ PAUSE",
    "connecting": "⏳ Connecting...",
    "error_prefix": "Error: ",
    "play_button": "▶️ LISTEN LIVE",
    "stream_stopped": "Stream stopped"
};

// Function to get a translation
function t(key, fallback = "") {
    return translations[key] || fallback || key;
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { translations, t };
}