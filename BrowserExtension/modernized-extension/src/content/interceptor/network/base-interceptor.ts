/**
 * Base Network Interceptor
 * 
 * Provides common functionality and types for network interceptors
 */

import { InterceptedRequest } from '../../../shared/types';

/**
 * Base class for network interceptors
 */
export abstract class BaseInterceptor {
  protected config = {
    debug: {
      enabled: true,
      logNetworkRequests: false,
      logResponseDetails: true
    }
  };
  
  protected requestIdCounter = 0;
  
  /**
   * Initialize the interceptor
   */
  public abstract initialize(): void;
  
  /**
   * Check if a URL should be intercepted based on endpoint patterns
   */
  protected shouldInterceptUrl(url: string, subscribedEndpoints: string[]): boolean {
    let urlObj: URL;
    
    try {
      urlObj = new URL(url);
    } catch (e) {
      return false;
    }
    
    // Extract the action/endpoint name
    const segments = urlObj.pathname.split('?')[0].split('/').filter(Boolean);
    const actionName = segments.pop();
    
    if (!actionName) return false;
    
    return subscribedEndpoints.includes(actionName);
  }
  
  /**
   * Dispatch a SaveBatch event to the content script
   */
  protected dispatchSaveBatchEvent(data: InterceptedRequest): void {
    this.log(`Dispatching SaveBatch event for ${data.id}`, 'debug');
    
    // Create and dispatch event
    const event = new CustomEvent('SaveBatch', {
      detail: data
    });
    
    window.dispatchEvent(event);
  }
  
  /**
   * Log a message with the appropriate level
   */
  protected log(message: string, level: 'debug' | 'info' | 'warn' | 'error' = 'info'): void {
    const prefix = 'DIY-MOD Interceptor:';
    
    switch(level) {
      case 'debug':
        if (this.config.debug.enabled) {
          console.debug(prefix, message);
        }
        break;
      case 'info':
        console.log(prefix, message);
        break;
      case 'warn':
        console.warn(prefix, message);
        break;
      case 'error':
        console.error(prefix, message);
        break;
    }
  }
}