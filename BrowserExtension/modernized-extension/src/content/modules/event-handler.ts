/**
 * Event Handler Module
 * 
 * Provides functionality for handling events between content and injected scripts.
 */

import { logger } from '@/utils/logger';
import { InterceptedRequest } from '@/shared/types';
import { getCurrentPlatform } from './platform-detector';
import { processWithWebSocket } from './websocket-connector';

/**
 * Set up event listeners for communication with injected script
 */
export function setupEventListeners(): void {
  // Listen for SaveBatch events from the injected script
  window.addEventListener('SaveBatch', function(event: CustomEvent<InterceptedRequest>) {
    logger.content.debug('Received SaveBatch event:', { 
      id: event.detail?.id,
      type: event.detail?.type
    });
    
    // Process the intercepted request
    handleInterceptedRequest(event.detail);
  });
  
  // Also listen for message events as a fallback
  window.addEventListener('message', function(event) {
    if (event.source !== window) return;
    
    // Forward settings requests to background
    if (event.data?.type === 'getSettings') {
      try {
        chrome.runtime.sendMessage({ type: 'getSettings' }, response => {
          if (chrome.runtime.lastError) {
            logger.content.warn('Settings request failed:', chrome.runtime.lastError);
            // Send default settings if extension context is invalid
            window.postMessage({ 
              type: 'settingsResponse',
              settings: {
                blurHoverEffect: true,
                blurIntensity: 8
              }
            }, '*');
            return;
          }
          
          window.postMessage({ 
            type: 'settingsResponse',
            settings: response?.settings || {
              blurHoverEffect: true,
              blurIntensity: 8
            }
          }, '*');
        });
      } catch (error) {
        logger.content.warn('Extension context invalidated, using default settings:', error);
        // Send default settings if extension context is invalid
        window.postMessage({ 
          type: 'settingsResponse',
          settings: {
            blurHoverEffect: true,
            blurIntensity: 8
          }
        }, '*');
      }
    }
  });
}

/**
 * Handle an intercepted request
 */
async function handleInterceptedRequest(data: InterceptedRequest): Promise<void> {
  try {
    if (!data) {
      logger.content.error('Invalid data received from injected script');
      return;
    }
    
    logger.content.info(`Processing intercepted ${data.type} request`, { 
      id: data.id,
      url: data.url
    });
    
    // Make sure we have response data
    if (!data.response) {
      logger.content.error('No response data in intercepted request');
      sendOriginalResponse(data);
      return;
    }
    
    // Get the platform
    const platform = getCurrentPlatform();
    if (!platform) {
      logger.content.error('Could not determine platform for request');
      sendOriginalResponse(data);
      return;
    }
    
    try {
      // Process the feed using WebSocket with HTTP fallback
      const result = await processWithWebSocket(data, platform);
      
      // Validate response format
      if (!result || !result.feed || !result.feed.response) {
        throw new Error('Invalid response format from server');
      }
      
      // Extract the processed content
      const processedResponse = result.feed.response;
      
      // Send the processed response back to the injected script
      window.dispatchEvent(new CustomEvent('CustomFeedReady', {
        detail: {
          id: data.id,
          url: data.url,
          response: processedResponse
        }
      }));      
    } catch (error) {
      logger.content.error('Error processing content through server:', error);
      console.error('DIY-MOD: Server communication error:', error);
      
      // Send the original response back to avoid blocking the page
      sendOriginalResponse(data);
    }
  } catch (error) {
    logger.content.error('Error handling intercepted request:', error);
    
    // Send the original response back to avoid blocking the page
    sendOriginalResponse(data);
  }
}

/**
 * Send the original response back when processing fails
 */
function sendOriginalResponse(data: InterceptedRequest): void {
  window.dispatchEvent(new CustomEvent('CustomFeedReady', {
    detail: {
      id: data.id,
      url: data.url,
      response: data.response
    }
  }));
} 