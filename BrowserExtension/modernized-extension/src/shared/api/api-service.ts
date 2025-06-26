import { config } from '../config';
import { Filter, FeedResponse, LLMResponse, ServerResponse } from '../types';
import { logger } from '../../utils/logger';
import { client } from '../client';

/**
 * API Service for DIY-MOD extension
 * Handles all communication with the backend API
 */
class ApiService {
  /**
   * Process a feed with the backend API
   */
  async processFeed(
    url: string,
    userId: string,
    platform: string,
    responseData: string,
    options: { useBatching?: boolean } = {}
  ): Promise<FeedResponse> {
    try {
      logger.api.info(`Processing ${platform} feed from ${url}`);
      
      // Get authenticated user info for token
      let userInfo;
      try {
        userInfo = await this.getUserInfo();
      } catch (error) {
        logger.api.warn('Failed to get user info, continuing without auth token:', error);
        userInfo = null;
      }
      
      const authToken = userInfo?.token;
      
      // const endpoint = options.useBatching && config.api.batchingEnabled ? '/batch' : '/process';
      const requestBody = {
        tab_id: chrome.runtime.id,
        user_id: userId,
        url: url,
        extension_version: config.version,
        useBatching: options.useBatching || false,
        data: JSON.stringify({
          feed_info: {
            response: responseData
          }
        })
      };
      
      // Use the batch client if batching is enabled
      if (options.useBatching && config.api.batchingEnabled) {
        logger.api.debug('Using batch client for feed processing');
        
        // Wrap the request in a Promise
        return new Promise((resolve, reject) => {
          client.postRequest(
            config.api.endpoints.process,
            requestBody,
            (data) => resolve(data),
            (error) => reject(new Error(error))
          );
        });
      } else {
        // Standard request using fetch
        const response = await fetch(`${config.api.baseUrl}${config.api.endpoints.process}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': authToken ? `Bearer ${authToken}` : ''
          },
          body: JSON.stringify(requestBody)
        });
        
        if (!response.ok) {
          throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        return result;
      }
    } catch (error) {
      logger.api.error('Error processing feed:', error);
      throw error;
    }
  }
  
  /**
   * Process content through the backend API
   * @param posts Array of posts to process
   */
  async processContent(posts: any[]): Promise<any[]> {
    try {
      logger.api.info(`Processing ${posts.length} posts`);
      
      const userId = await this.getUserId();
      
      // Format the request body
      const requestBody = {
        tab_id: chrome.runtime.id,
        user_id: userId,
        extension_version: config.version,
        data: JSON.stringify({
          posts: posts
        })
      };
      
      const response = await fetch(`${config.api.baseUrl}/process_content`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
      });
      
      if (!response.ok) {
        throw new Error(`Server returned ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      return result.processed_posts || [];
    } catch (error) {
      logger.api.error('Error processing content:', error);
      throw error;
    }
  }

  /**
   * Process multiple content items in parallel
   * @param items Array of content items to process
   * @param userId User ID
   * @param url URL being accessed
   */
  async processContentItems(
    items: { id: string, content: string }[],
    userId: string,
    url: string
  ): Promise<any[]> {
    try {
      // Check if parallel processing is enabled
      if (!config.api.parallelRequestsEnabled) {
        throw new Error('Parallel requests are disabled in configuration');
      }
      
      logger.api.info(`Processing ${items.length} content items in parallel`);
      
      // Prepare parallel requests
      const requests = items.map(item => {
        return {
          path: config.api.endpoints.process,
          params: {
            tab_id: chrome.runtime.id,
            user_id: userId,
            url: url,
            extension_version: config.version,
            item_id: item.id,
            data: JSON.stringify({
              feed_info: {
                response: item.content
              }
            })
          }
        };
      });
      
      // Use the parallel execution feature of the client
      const results = await client.executeParallel(requests);
      
      // Return results with their IDs
      return results.map((result, index) => ({
        id: items[index].id,
        result
      }));
    } catch (error) {
      logger.api.error('Error in parallel content processing:', error);
      throw error;
    }
  }
  
  /**
   * Send a chat message to the LLM
   * @param message Message content
   * @param history Previous conversation history
   * @param options Additional options including batching
   */
  async sendChatMessage(
    message: string,
    history: any[] = [],
    options: { useBatching?: boolean, batchId?: string } = {}
  ): Promise<LLMResponse> {
    try {
      logger.api.info('Sending chat message to LLM');
      
      const userId = await this.getUserId();
      
      const requestParams = {
        message,
        history,
        user_id: userId
      };
      
      // Use batching if enabled and requested
      if (options.useBatching && config.api.batchingEnabled && options.batchId) {
        logger.api.debug(`Adding message to batch: ${options.batchId}`);
        
        // Add to specified batch and return a Promise
        return new Promise<LLMResponse>((resolve) => {
          // Add to batch but ignore the returned ID for now
          client.addToBatch(
            options.batchId || 'default',
            '/chat',
            requestParams
          );
          
          // Note: This doesn't wait for the batch to complete
          // The caller should use client.executeBatch() when ready
          
          // For now, resolve with a placeholder to maintain interface compatibility
          resolve({
            status: 'pending',
            message: 'Added to batch, waiting for execution',
            response: '',
            pending: true,
            batch_id: options.batchId
          } as any);
        });
      } else {
        // Standard request using fetch
        const response = await fetch(`${config.api.baseUrl}/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(requestParams)
        });
        
        if (!response.ok) {
          throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        return result;
      }
    } catch (error) {
      logger.api.error('Error in chat processing:', error);
      throw error;
    }
  }
  
  /**
   * Send multiple chat messages to LLMs in parallel
   * @param messages Array of messages with associated metadata
   * @param userId User ID
   */
  async sendParallelChatMessages(
    messages: Array<{
      message: string;
      history?: any[];
      metadata?: any;
    }>
  ): Promise<any[]> {
    try {
      // Check if parallel processing is enabled
      if (!config.api.parallelRequestsEnabled) {
        throw new Error('Parallel requests are disabled in configuration');
      }
      
      logger.api.info(`Sending ${messages.length} chat messages in parallel`);
      
      const userId = await this.getUserId();
      
      // Prepare parallel requests
      const requests = messages.map(item => {
        return {
          path: '/chat',
          params: {
            message: item.message,
            history: item.history || [],
            user_id: userId,
            metadata: item.metadata
          }
        };
      });
      
      // Use the parallel execution feature of the client
      return await client.executeParallel(requests);
    } catch (error) {
      logger.api.error('Error in parallel chat processing:', error);
      throw error;
    }
  }
  
  /**
   * Send an image for processing
   */
  async processImage(
    image: File,
    message?: string,
    history: any[] = []
  ): Promise<LLMResponse> {
    try {
      logger.api.info('Processing image with LLM');
      
      const userId = await this.getUserId();
      
      const formData = new FormData();
      formData.append('image', image);
      
      if (message) {
        formData.append('message', message);
      }
      
      formData.append('history', JSON.stringify(history));
      formData.append('user_id', userId);
      
      const response = await fetch(`${config.api.baseUrl}/chat/image`, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        throw new Error(`Server returned ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      return result;
    } catch (error) {
      logger.api.error('Error processing image:', error);
      throw error;
    }
  }
  
  /**
   * Get user filters from the server
   */
  async getUserFilters(): Promise<Filter[]> {
    try {
      const userId = await this.getUserId();
      
      const response = await fetch(`${config.api.baseUrl}/filters?user_id=${userId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error(`Server returned ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      if (data.status !== 'success') {
        throw new Error(data.message || 'Unknown error getting user filters');
      }
      
      return data.filters || [];
    } catch (error) {
      logger.api.error('Error getting user filters:', error);
      throw error;
    }
  }
  
  /**
   * Create a new filter
   */
  async createFilter(filterData: {
    filter_text: string;
    content_type: 'text' | 'image' | 'all';
    duration: string;
  }): Promise<ServerResponse<any>> {
    try {
      const userId = await this.getUserId();
      
      const response = await fetch(`${config.api.baseUrl}/filters`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          user_id: userId,
          intensity: 5,  // Always use maximum intensity level
          ...filterData
        })
      });
      
      if (!response.ok) {
        throw new Error(`Server returned ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      return result;
    } catch (error) {
      logger.api.error('Error creating filter:', error);
      throw error;
    }
  }
  
  /**
   * Delete a filter
   */
  async deleteFilter(filterId: string): Promise<ServerResponse<any>> {
    try {
      const userId = await this.getUserId();
      
      const response = await fetch(`${config.api.baseUrl}/filters/${filterId}?user_id=${userId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error(`Server returned ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      return result;
    } catch (error) {
      logger.api.error('Error deleting filter:', error);
      throw error;
    }
  }
  
  /**
   * Update an existing filter
   */
  async updateFilter(filterId: string, filterData: {
    filter_text: string;
    content_type: 'text' | 'image' | 'all';
    duration: string;
  }): Promise<ServerResponse<any>> {
    try {
      const userId = await this.getUserId();
      
      const response = await fetch(`${config.api.baseUrl}/filters/${filterId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          user_id: userId,
          intensity: 5,  // Always use maximum intensity level
          ...filterData
        })
      });
      
      if (!response.ok) {
        throw new Error(`Server returned ${response.status}: ${response.statusText}`);
      }
      
      const result = await response.json();
      return result;
    } catch (error) {
      logger.api.error('Error updating filter:', error);
      throw error;
    }
  }
  
  /**
   * Test connection to the server
   */
  async testConnection(): Promise<ServerResponse<boolean>> {
    try {
      const response = await fetch(`${config.api.baseUrl}/ping`, {
        method: 'GET'
      });
      
      if (!response.ok) {
        return { status: 'error', message: `Server returned ${response.status}` };
      }
      
      return { status: 'success', data: true };
    } catch (error) {
      logger.api.error('Error testing connection:', error);
      return { status: 'error', message: (error as Error).message };
    }
  }
  
  /**
   * Get user ID from storage
   */
  async getUserId(): Promise<string> {
    return new Promise((resolve, reject) => {
      chrome.storage.sync.get(['user_id'], result => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }
        
        if (!result.user_id) {
          reject(new Error('User ID not found in storage'));
          return;
        }
        
        resolve(result.user_id);
      });
    });
  }

  /**
   * Get the authenticated user info
   */
  async getUserInfo(): Promise<{ id: string; token?: string } | null> {
    return new Promise((resolve) => {
      try {
        chrome.runtime.sendMessage({ type: 'getUserInfo' }, (response) => {
          // Check for extension context invalidated error
          if (chrome.runtime.lastError) {
            console.warn('Extension context invalidated, falling back to storage-based user ID');
            // Fall back to getting user ID directly from storage
            chrome.storage.sync.get(['user_id'], (result) => {
              if (result.user_id) {
                resolve({ id: result.user_id });
              } else {
                resolve(null);
              }
            });
            return;
          }
          resolve(response?.user || null);
        });
      } catch (error) {
        console.warn('Error getting user info, falling back to storage:', error);
        // Fall back to getting user ID directly from storage
        chrome.storage.sync.get(['user_id'], (result) => {
          if (result.user_id) {
            resolve({ id: result.user_id });
          } else {
            resolve(null);
          }
        });
      }
    });
  }
}

// Export as singleton
export const apiService = new ApiService();