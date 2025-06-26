/**
 * Logger utility for consistent logging across the extension
 */
import { config } from '../shared/config';

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

const LOG_LEVELS: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3
};

class Logger {
  private context: string;
  
  constructor(context: string) {
    this.context = context;
  }
  
  /**
   * Check if the current log level should be displayed
   */
  private shouldLog(level: LogLevel): boolean {
    const configLevel = config.logging.level;
    return LOG_LEVELS[level] >= LOG_LEVELS[configLevel];
  }
  
  /**
   * Format log message with timestamp and context
   */
  private formatMessage(message: string): string {
    const timestamp = new Date().toISOString();
    return `[${timestamp}] [${this.context}] ${message}`;
  }
  
  /**
   * Send logs to remote logging service if enabled
   */
  private async remoteLog(level: LogLevel, message: string, data?: any): Promise<void> {
    if (!config.logging.enableRemoteLogging) return;
    
    try {
      const payload = {
        level,
        message,
        context: this.context,
        timestamp: new Date().toISOString(),
        data: data || null
      };
      
      await fetch(`${config.api.baseUrl}/logging`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });
    } catch (error) {
      // Don't log errors from the remote logger to avoid loops
      console.error('Remote logging failed:', error);
    }
  }
  
  /**
   * Log a debug message
   */
  debug(message: string, data?: any): void {
    if (!this.shouldLog('debug')) return;
    console.debug(this.formatMessage(message), data || '');
    this.remoteLog('debug', message, data);
  }
  
  /**
   * Log an info message
   */
  info(message: string, data?: any): void {
    if (!this.shouldLog('info')) return;
    console.info(this.formatMessage(message), data || '');
    this.remoteLog('info', message, data);
  }
  
  /**
   * Log a warning message
   */
  warn(message: string, data?: any): void {
    if (!this.shouldLog('warn')) return;
    console.warn(this.formatMessage(message), data || '');
    this.remoteLog('warn', message, data);
  }
  
  /**
   * Log an error message
   */
  error(message: string, error?: any): void {
    if (!this.shouldLog('error')) return;
    console.error(this.formatMessage(message), error || '');
    this.remoteLog('error', message, error);
  }
}

/**
 * Create a logger for the given context
 */
export function createLogger(context: string): Logger {
  return new Logger(context);
}

/**
 * Export default logger instances
 */
export const logger = {
  content: createLogger('content'),
  background: createLogger('background'),
  popup: createLogger('popup'),
  api: createLogger('api')
};