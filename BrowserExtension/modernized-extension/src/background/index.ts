/**
 * DIY-MOD Extension Background Script
 * 
 * Handles background tasks, user identification, and communication with content scripts
 */
import { config, loadConfig, isDevelopment } from '../shared/config';
import { client } from '../shared/client';

console.log('DIY-MOD Background Script initialized');

// Default settings
const defaultSettings = {
  enabled: true,
  blurHoverEffect: true,
  blurIntensity: 8,
  overlayStyle: 'dark',
  showOverlayBorder: true,
  overlayBorderWidth: 1,
  overlayBorderColor: 'rgb(0, 119, 255)',
  showRewriteBorder: true,
  rewriteBorderWidth: 1,
  rewriteBorderColor: '#ffd700',
  darkMode: true,
  accentColor: 'rgb(0, 119, 255)',
  imageProcessing: {
    enabled: true,
    maxPostsWithImages: 5,
    maxImagesPerPost: 2
  }
};

// User authentication state
interface GoogleUserInfo {
  id: string;
  email?: string;
  name?: string;
  picture?: string;
  token?: string;
}

// Generate a unique user ID if not already present
async function initializeUserId(): Promise<void> {
  const data = await chrome.storage.sync.get(['user_id']);
  if (!data.user_id) {
    const newUserId = crypto.randomUUID();
    await chrome.storage.sync.set({ user_id: newUserId });
    console.log('New user ID generated:', newUserId);
  }
}

// Sign in with Google and replace the anonymous ID
async function signInWithGoogle(): Promise<GoogleUserInfo | null> {
  try {
    console.log('DIY-MOD: Initiating Google authentication');
    
    // Launch Google auth flow
    const token = await launchGoogleAuthFlow();
    if (!token) {
      console.log('DIY-MOD: No auth token received');
      return null;
    }
    
    // Get user info using the token
    const userInfo = await fetchGoogleUserInfo(token);
    if (!userInfo || !userInfo.id) {
      console.error('DIY-MOD: Failed to get valid user info');
      return null;
    }
    
    // Replace user_id with the Google ID
    await chrome.storage.sync.set({ user_id: userInfo.id });
    
    // Store Google info separately (without replacing user_id)
    await chrome.storage.sync.set({ google_user_info: userInfo });
    
    // Update config with user ID
    config.userId = userInfo.id;
    
    console.log('DIY-MOD: Google authentication successful for', userInfo.email);
    return userInfo;
  } catch (error) {
    console.error('DIY-MOD: Google authentication error:', error);
    return null;
  }
}

// Launch the Google OAuth flow
async function launchGoogleAuthFlow(): Promise<string | null> {
  return new Promise((resolve) => {
    chrome.identity.getAuthToken({ interactive: true }, (token) => {
      if (chrome.runtime.lastError) {
        console.error('Auth error:', chrome.runtime.lastError.message);
        resolve(null);
        return;
      }
      
      if (!token) {
        console.error('No token received');
        resolve(null);
        return;
      }
      
      resolve(token);
    });
  });
}

// Fetch user info from Google APIs
async function fetchGoogleUserInfo(token: string): Promise<GoogleUserInfo | null> {
  try {
    const response = await fetch(
      'https://www.googleapis.com/oauth2/v1/userinfo?alt=json', {
        headers: { Authorization: `Bearer ${token}` }
      }
    );
    
    if (!response.ok) {
      throw new Error(`Failed to fetch user info: ${response.status}`);
    }
    
    const data = await response.json();
    
    return {
      id: data.id,
      email: data.email,
      name: data.name,
      picture: data.picture,
      token: token
    };
  } catch (error) {
    console.error('Failed to fetch Google user info:', error);
    return null;
  }
}

// Sign out and revert to a new anonymous ID
async function signOut(): Promise<boolean> {
  try {
    // Get Google info
    const data = await chrome.storage.sync.get(['google_user_info']);
    if (data.google_user_info?.token) {
      // Revoke the token
      await fetch(`https://accounts.google.com/o/oauth2/revoke?token=${data.google_user_info.token}`);
      
      // Remove the cached token
      chrome.identity.removeCachedAuthToken({ token: data.google_user_info.token });
    }
    
    // Remove Google user info
    await chrome.storage.sync.remove(['google_user_info']);
    
    // Generate a new anonymous ID
    const newUserId = crypto.randomUUID();
    await chrome.storage.sync.set({ user_id: newUserId });
    
    // Update config
    config.userId = newUserId;
    
    console.log('DIY-MOD: User signed out successfully, new anonymous ID generated');
    return true;
  } catch (error) {
    console.error('DIY-MOD: Sign out error:', error);
    return false;
  }
}

// Get current user info
async function getUserInfo(): Promise<{
  id: string;
  isGoogle: boolean;
  email?: string;
  user?: {
    name?: string;
    email?: string;
    picture?: string;
  }
}> {
  // Check if we have Google info
  const data = await chrome.storage.sync.get(['user_id', 'google_user_info']);
  
  if (data.google_user_info) {
    return {
      id: data.user_id,
      isGoogle: true,
      user: {
        name: data.google_user_info.name,
        email: data.google_user_info.email,
        picture: data.google_user_info.picture
      }
    };
  }
  
  return {
    id: data.user_id,
    isGoogle: false
  };
}

// Load settings from storage
async function loadSettings(): Promise<any> {
  const data = await chrome.storage.sync.get(['settings']);
  return data.settings || defaultSettings;
}

// Save settings to storage
async function saveSettings(settings: any): Promise<void> {
  await chrome.storage.sync.set({ settings });
}

// Test server connection to ensure API is reachable
async function checkServerConnection(): Promise<boolean> {
  try {
    const pingUrl = `${config.api.baseUrl}/ping`;
    const response = await fetch(pingUrl, { method: 'GET' });
    
    const isConnected = response.ok;
    console.log(`DIY-MOD: Server connection ${isConnected ? 'successful' : 'failed'}`);
    return isConnected;
  } catch (error) {
    console.error('DIY-MOD: Server connection test failed:', error);
    return false;
  }
}

/**
 * Poll for image processing result
 * This function runs in the background context to avoid CSP restrictions
 */
async function pollForImageResult(imageUrl: string, filters: string[]): Promise<any> {
  try {
    // Use the polling endpoint from config
    const pollingBaseUrl = config.api?.pollingBaseUrl || 'http://localhost:5000';
    const imageResultEndpoint = config.api?.endpoints?.imageResult || '/get_img_result';
    
    // Construct the URL
    const filtersParam = encodeURIComponent(JSON.stringify(filters));
    const imgUrlParam = encodeURIComponent(imageUrl);
    const pollUrl = `${pollingBaseUrl}${imageResultEndpoint}?img_url=${imgUrlParam}&filters=${filtersParam}`;
    
    // Make the request
    console.log('DIY-MOD Background: Polling for image result:', pollUrl);
    const response = await fetch(pollUrl);
    const data = await response.json();
    
    return data;
  } catch (error) {
    console.error('DIY-MOD Background: Error polling for image result:', error);
    throw error;
  }
}

// Listen for messages from content scripts or popup
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === 'getStatus') {
    sendResponse({ 
      status: 'active', 
      version: config.version,
      mode: isDevelopment() ? 'development' : 'production',
      logging: config.logging.level
    });
    return true;
  }
  
  // Handle style update requests from options page
  if (message.type === 'updateStyles' && message.cssVariables) {
    console.log('DIY-MOD: Forwarding style updates to content scripts');
    
    // Forward CSS variables to supported sites
    chrome.tabs.query({
      url: [
        "*://*.twitter.com/*",
        "*://*.x.com/*",
        "*://*.reddit.com/*"
      ]
    }, tabs => {
      tabs.forEach(tab => {
        if (tab.id) {
          chrome.tabs.sendMessage(tab.id, {
            type: 'updateStyles',
            cssVariables: message.cssVariables
          }).catch(err => {
            // Ignore errors for tabs where content script isn't loaded
            console.debug(`Tab ${tab.id} not ready for style update:`, err);
          });
        }
      });
    });
    
    // Send success response back to options page
    sendResponse({ success: true });
    return true;
  }
  
  if (message.type === 'getSettings') {
    loadSettings().then(settings => {
      // Ensure darkMode and accentColor are set
      if (settings.overlayStyle === 'dark' && settings.darkMode === undefined) {
        settings.darkMode = true;
      }
      if (!settings.accentColor && settings.overlayBorderColor) {
        settings.accentColor = settings.overlayBorderColor;
      }
      
      sendResponse({ settings });
    }).catch(error => {
      console.error('Error loading settings:', error);
      sendResponse({ settings: defaultSettings });
    });
    
    // Return true to indicate we'll respond asynchronously
    return true;
  }
  
  if (message.type === 'updateSettings') {
    loadSettings().then(currentSettings => {
      const newSettings = { ...currentSettings, ...message.settings };
      return saveSettings(newSettings).then(() => {
        // Notify all tabs about the settings change
        chrome.tabs.query({}, tabs => {
          tabs.forEach(tab => {
            if (tab.id) {
              chrome.tabs.sendMessage(tab.id, { 
                type: 'settingsUpdated',
                settings: newSettings
              }).catch(() => {
                // Ignore errors for tabs where content script isn't loaded
              });
            }
          });
        });
        sendResponse({ success: true, settings: newSettings });
      });
    }).catch(error => {
      console.error('Error updating settings:', error);
      sendResponse({ success: false, error: error.message });
    });
    
    // Return true to indicate we'll respond asynchronously
    return true;
  }

  if (message.type === 'testConnection') {
    checkServerConnection().then(isConnected => {
      sendResponse({ connected: isConnected });
    }).catch(error => {
      console.error('Error testing connection:', error);
      sendResponse({ connected: false, error: error.message });
    });
    
    // Return true to indicate we'll respond asynchronously
    return true;
  }
  
  if (message.type === 'signIn') {
    signInWithGoogle().then(userInfo => {
      sendResponse({ success: !!userInfo, user: userInfo });
    }).catch(error => {
      console.error('Sign in error:', error);
      sendResponse({ success: false, error: error.message });
    });
    return true;
  }
  
  if (message.type === 'signOut') {
    signOut().then(success => {
      sendResponse({ success });
    }).catch(error => {
      console.error('Sign out error:', error);
      sendResponse({ success: false, error: error.message });
    });
    return true;
  }
  
  if (message.type === 'getUserInfo') {
    getUserInfo().then(userInfo => {
      sendResponse({ user: userInfo });
    }).catch(error => {
      console.error('Error getting user info:', error);
      sendResponse({ user: null, error: error.message });
    });
    return true;
  }
  
  // Handle image result polling to avoid CSP restrictions
  if (message.type === 'pollImageResult') {
    const { imageUrl, filters } = message;
    
    pollForImageResult(imageUrl, filters)
      .then(result => {
        sendResponse({ success: true, result });
      })
      .catch(error => {
        sendResponse({ success: false, error: error.message });
      });
      
    return true;
  }
});

// Handle port connections for settings sync
chrome.runtime.onConnect.addListener(port => {
  if (port.name === "settings-sync") {
    port.onDisconnect.addListener(() => {
      console.log('Settings sync port disconnected');
    });
  }
});

// Initialize on extension installation
chrome.runtime.onInstalled.addListener(async () => {
  console.log('DIY-MOD Extension installed');
  
  try {
    // Load config
    await loadConfig();
    
    // Initialize user ID (anonymous)
    await initializeUserId();
    
    // Set default settings if not already present
    const settings = await loadSettings();
    if (!settings) {
      await saveSettings(defaultSettings);
    }
    
    // Test server connection
    // const isConnected = await checkServerConnection();
    // console.log(`DIY-MOD: Server connection on installation: ${isConnected ? 'successful' : 'failed'}`);
    
    // Log events if connected
    if (config.userId) {
      client.logEvent('extension_installed', {
        version: config.version,
        browser: navigator.userAgent
      });
    }
  } catch (error) {
    console.error('DIY-MOD: Error during initialization:', error);
  }
});

// Initialize on startup
Promise.all([
  loadConfig(),
  initializeUserId().then(() => {
    // Get the user ID after initialization
    return chrome.storage.sync.get(['user_id']);
  })
])
.then(results => {
  const userData = results[1];
  if (userData.user_id) {
    config.userId = userData.user_id;
  }
  
  console.log('DIY-MOD: Extension initialized with config:', {
    api: config.api.baseUrl,
    logging: config.logging.level,
    userId: config.userId || 'Not set'
  });
  
  // Test server connection
  return checkServerConnection();
})
.then(isConnected => {
  if (isConnected && config.userId) {
    client.logEvent('extension_activated', { 
      version: config.version 
    });
  }
})
.catch(error => {
  console.error('DIY-MOD: Error during initialization:', error);
});