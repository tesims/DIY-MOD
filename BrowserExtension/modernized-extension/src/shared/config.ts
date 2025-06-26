/**
 * Configuration for DIY-MOD Extension
 * Central place for all configuration settings
 */

import { Platform } from './types';

interface UserPreferences {
  // Visual preferences
  blurIntensity?: number;
  blurHoverEffect?: boolean;
  overlayStyle?: 'dark' | 'light';
  overlayBorderColor?: string;
  overlayBorderWidth?: number;
  showOverlayBorder?: boolean;
  rewriteBorderColor?: string;
  rewriteBorderWidth?: number;
  showRewriteBorder?: boolean;
  syncBorders?: boolean;
  
  // Processing preferences
  processingMode?: 'balanced' | 'aggressive';
  defaultContentType?: 'all' | 'text' | 'image';
  defaultDuration?: 'permanent' | 'day' | 'week' | 'month';
}

interface Config {
  version: string;
  userId: string | null;
  api: {
    baseUrl: string;
    pollingBaseUrl: string; // Added polling base URL
    endpoints: {
      process: string;
      settings: string;
      filters: string;
      stats: string;
      imageResult: string; // Added endpoint for image result polling
    };
    maxRetries: number;
    requestTimeoutMs: number;
    batchTimeoutMs: number;
    batchingEnabled: boolean;
    parallelRequestsEnabled: boolean;
    maxParallelRequests: number;
    websocketEnabled: boolean; // Enable WebSocket processing
    polling: {
      maxAttempts: number; // Added max attempts for polling
      intervalMs: number;  // Added polling interval in milliseconds
    };
  };
  features: {
    contentFiltering: boolean;
    imageProcessing: boolean;
    analytics: boolean;
    userPreferences: boolean;
    hideInitialPosts: boolean; // Whether to hide the first few posts on social media sites
  };
  platforms: {
    [key in Platform]: {
      enabled: boolean;
      name: string;
      url: string;
      interceptPatterns: string[];
      selectors: {
        [key: string]: string;
      };
    }
  };
  logging: {
    enabled: boolean;
    level: 'debug' | 'info' | 'warn' | 'error';
    enableRemoteLogging: boolean;
  };
  userPreferences: UserPreferences;
}

/**
 * Determine if we're in development mode based on both extension manifest and environment
 */
export function isDevelopment(): boolean {
  try {
    // First check for explicit development flag in storage
    const devFlag = localStorage.getItem('diy_mod_dev_mode');
    if (devFlag === 'true') {
      return true;
    }
    if (devFlag === 'false') {
      return false;
    }
    
    // Check if we're in dev mode by looking for update_url in manifest
    const manifest = chrome.runtime.getManifest();
    const isDevExtension = !('update_url' in manifest);
    
    // Try to access NODE_ENV from environment if available (for building)
    const isDevEnv = typeof process !== 'undefined' && 
      typeof process.env !== 'undefined' && 
      process.env.NODE_ENV === 'development';
      
    return isDevExtension || isDevEnv;
  } catch {
    // Default to production if we can't determine
    return false;
  }
}

/**
 * Get the appropriate API configuration based on environment
 */
function getApiConfig() {
  const isLocalDev = isDevelopment();
  
  if (isLocalDev) {
    // Local development configuration - using SSH tunnel to EC2
    return {
      baseUrl: 'http://localhost:5001',  // SSH tunnel to remote server
      pollingBaseUrl: 'http://localhost:5001',
      maxRetries: 2,  // Faster feedback in development
      requestTimeoutMs: 90000,  // Extended timeout for WebSocket processing (90 seconds)
      polling: {
        maxAttempts: 10,  // Fewer attempts for faster iteration
        intervalMs: 3000,  // Faster polling for development
      },
    };
  } else {
    // Production configuration (via SSH tunnel)
    return {
      baseUrl: 'http://localhost:5001',  // SSH tunnel to EC2 instance
      pollingBaseUrl: 'http://localhost:5001',
      maxRetries: 3,
      requestTimeoutMs: 60000,
      polling: {
        maxAttempts: 20,
        intervalMs: 8000,
      },
    };
  }
}

// Default configuration
export const config: Config = {
  version: '1.0.0',
  userId: null,
  api: {
    ...getApiConfig(),
    endpoints: {
      // Match the original vanilla implementation endpoints exactly
      process: '/get_feed',
      settings: '/settings',
      filters: '/filters',
      stats: '/stats',
      imageResult: '/get_img_result', // Endpoint for checking image processing status
    },
    batchTimeoutMs: 100,
    batchingEnabled: false,
    parallelRequestsEnabled: true,
    maxParallelRequests: 5,
    websocketEnabled: true, // Enable WebSocket by default
  },
  userPreferences: {
    // Visual settings
    blurIntensity: 8,
    blurHoverEffect: true,
    overlayStyle: 'dark',
    overlayBorderColor: '#0077ff',
    overlayBorderWidth: 1,
    showOverlayBorder: true,
    rewriteBorderColor: '#ffd700',
    rewriteBorderWidth: 1,
    showRewriteBorder: true,
    syncBorders: false,
    
    // Processing settings
    processingMode: 'balanced',
    defaultContentType: 'all',
    defaultDuration: 'permanent',
  },
  features: {
    contentFiltering: true,
    imageProcessing: true,
    analytics: true,
    userPreferences: true,
    hideInitialPosts: false, // Whether to hide the first few posts on social media sites
  },
  platforms: {
    reddit: {
      enabled: true,
      name: 'Reddit',
      url: 'reddit.com',
      interceptPatterns: [
        '*://www.reddit.com/*',
        '*://reddit.com/*',
        '*://*.reddit.com/*/comments/*',
        '*://*.reddit.com/r/*',
      ],
      selectors: {
        postTitle: 'div[slot="title"]',
        postContent: 'div[slot="text-body"]',
        postImage: 'div[slot="post-media-container"] img',
      },
    },
    twitter: {
      enabled: true,
      name: 'Twitter',
      url: 'twitter.com',
      interceptPatterns: [
        '*://twitter.com/*',
        '*://x.com/*',
        '*://twitter.com/home',
        '*://api.twitter.com/*',
      ],
      selectors: {
        tweetText: 'div[data-testid="tweetText"]',
        tweetImage: 'div[data-testid="tweetPhoto"]',
      },
    },
  },
  logging: {
    enabled: true,
    level: isDevelopment() ? 'debug' : 'info',  // Auto-adjust based on environment
    enableRemoteLogging: false,
  },
};

/**
 * Explicitly set development mode
 */
export function setDevelopmentMode(isDev: boolean): void {
  localStorage.setItem('diy_mod_dev_mode', isDev ? 'true' : 'false');
  
  // Update API configuration when development mode changes
  const newApiConfig = getApiConfig();
  Object.assign(config.api, newApiConfig);
  
  // Update logging level
  config.logging.level = isDev ? 'debug' : 'info';
  
  console.log(`DIY-MOD: Development mode manually set to: ${isDev}`);
  console.log(`DIY-MOD: API Base URL: ${config.api.baseUrl}`);
  console.log(`DIY-MOD: Logging level: ${config.logging.level}`);
}

/**
 * Check API server availability with retries
 */
export async function checkApiAvailability(retries: number = 3): Promise<boolean> {
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const response = await fetch(`${config.api.baseUrl}/ping`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000), // 5 second timeout
      });
      if (response.ok) {
        if (attempt > 1) {
          console.log(`DIY-MOD: API server connected on attempt ${attempt}`);
        }
        return true;
      }
    } catch (error) {
      if (attempt === retries) {
        console.warn(`DIY-MOD: API server at ${config.api.baseUrl} is not available after ${retries} attempts:`, error);
      } else {
        console.log(`DIY-MOD: API connection attempt ${attempt}/${retries} failed, retrying...`);
        // Wait before retry
        await new Promise(resolve => setTimeout(resolve, 2000));
      }
    }
  }
  return false;
}

/**
 * Initialize configuration and validate API connectivity
 */
export async function initializeConfig(): Promise<void> {
  await loadConfig();
  
  // Check API availability on initialization with more retries
  const isApiAvailable = await checkApiAvailability(5);
  if (!isApiAvailable) {
    console.warn(`DIY-MOD: Warning - API server at ${config.api.baseUrl} is not responding`);
    if (isDevelopment()) {
      console.warn('DIY-MOD: Make sure your local development server is running with: ./start_local_system.sh');
    } else {
      console.warn('DIY-MOD: Make sure your SSH tunnel is active. Run: ./create_tunnel_manager.sh status');
      console.warn('DIY-MOD: To start tunnel: ./create_tunnel_manager.sh start');
      console.warn('DIY-MOD: To monitor tunnel: ./create_tunnel_manager.sh monitor');
    }
  } else {
    console.log(`DIY-MOD: Successfully connected to API server at ${config.api.baseUrl}`);
  }
}

/**
 * Loads user ID from storage
 */
async function loadUserId(): Promise<string | null> {
  try {
    const storage = await chrome.storage.sync.get(['user_id']);
    console.log('DIY-MOD: storage: ', storage);
    if (storage.user_id) {
      return storage.user_id;
    }
    
    // Generate a new user ID if none exists
    if (!storage.user_id) {
      const newUserId = generateUserId();
      await chrome.storage.sync.set({ user_id: newUserId });
      return newUserId;
    }
    
    return null;
  } catch (error) {
    console.error('Failed to load user ID:', error);
    return null;
  }
}

/**
 * Generate a new user ID
 */
function generateUserId(): string {
  return Math.random().toString(36).substring(2, 15) + 'user_' + Math.random().toString(36).substring(2, 15);
}

/**
 * Loads custom configuration from storage if available
 */
export async function loadConfig(): Promise<void> {
  try {
    // Check if chrome.storage API is available
    if (!chrome || !chrome.storage || !chrome.storage.sync) {
      console.warn('DIY-MOD: chrome.storage.sync is not available, using default configuration');
      return; // Exit early and use default config
    }

    // First load the user ID
    config.userId = await loadUserId();
    
    // Then load stored configuration
    const storage = await chrome.storage.sync.get(['diy_mod_config']);
    
    if (storage.diy_mod_config) {
      // Merge stored config with default config, but don't overwrite userId
      const userId = config.userId;
      Object.assign(config, storage.diy_mod_config);
      config.userId = userId; // Ensure userId is preserved
    }
    
    // Update API configuration based on current environment
    const apiConfig = getApiConfig();
    Object.assign(config.api, apiConfig);
    
    // Set appropriate logging level
    if (isDevelopment()) {
      config.logging.level = 'debug';
      console.log('DIY-MOD: Running in development mode with debug logging enabled');
      console.log(`DIY-MOD: API Base URL: ${config.api.baseUrl}`);
    } else {
      console.log(`DIY-MOD: Running in production mode with ${config.logging.level} logging`);
      console.log(`DIY-MOD: API Base URL: ${config.api.baseUrl}`);
    }
  } catch (error) {
    console.error('Failed to load configuration:', error);
  }
}

/**
 * Set logging level and save it to storage
 */
export async function setLoggingLevel(level: 'debug' | 'info' | 'warn' | 'error'): Promise<void> {
  config.logging.level = level;
  await saveConfig();
}

/**
 * Save current configuration to storage
 */
export async function saveConfig(): Promise<void> {
  try {
    // Check if chrome.storage API is available
    if (!chrome || !chrome.storage || !chrome.storage.sync) {
      console.warn('DIY-MOD: chrome.storage.sync is not available, cannot save configuration');
      return;
    }
    
    await chrome.storage.sync.set({ diy_mod_config: config });
  } catch (error) {
    console.error('Failed to save configuration:', error);
  }
}

