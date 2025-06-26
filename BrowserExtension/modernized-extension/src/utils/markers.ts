import { MARKERS, CSS_CLASSES } from '../shared/constants';
import { DIY_IMG_ATTR } from '../shared/constants';
import { config } from '../shared/config';
// Destructure for cleaner code
const { BLUR_START, BLUR_END, OVERLAY_START, OVERLAY_END, REWRITE_START, REWRITE_END } = MARKERS;


/**
 * Type definitions for marker processor functions
 */
export type MarkerProcessor = (content: string) => string;
export type MarkerDetector = (content: string) => boolean;
export type ImageMarkerProcessor = (url: string) => string;
export type ImageMarkerDetector = (url: string) => boolean;

/**
 * Interface for registering text marker handlers
 */
export interface MarkerHandler {
  name: string;
  startMarker: string;
  endMarker: string;
  detect: MarkerDetector;
  process: MarkerProcessor;
}

/**
 * Interface for registering image marker handlers
 */
export interface ImageMarkerHandler {
  name: string;
  marker: string;
  detect: ImageMarkerDetector;
  process: ImageMarkerProcessor;
}

/**
 * Interface for tracking deferred image processing
 */
interface DeferredImageProcessing {
  imageElement: HTMLImageElement;
  originalUrl: string;
  filters: string[];
  config: any;
  pollCount: number;
  maxPolls: number;
}

/**
 * Registry of all marker handlers
 */
const markerHandlers: MarkerHandler[] = [];

/**
 * Registry of all image marker handlers
 */
const imageMarkerHandlers: ImageMarkerHandler[] = [];

/**
 * Tracking for deferred image processing
 */
const deferredImages: Map<string, DeferredImageProcessing> = new Map();

/**
 * Register a new marker handler
 * @param handler The marker handler to register
 */
export function registerMarkerHandler(handler: MarkerHandler): void {
  markerHandlers.push(handler);
  // console.log(`DIY-MOD: Registered marker handler for ${handler.name}`);
}

/**
 * Register a new image marker handler
 * @param handler The image marker handler to register
 */
export function registerImageMarkerHandler(handler: ImageMarkerHandler): void {
  imageMarkerHandlers.push(handler);
  console.log(`DIY-MOD: Registered image marker handler for ${handler.name}`);
}

/**
 * Process text with special markers to apply visual effects
 * @param text Text containing special markers
 * @returns HTML with appropriate styling applied
 */
export function processMarkedText(text: string): string {
  if (!text) return '';
  
  // Check if there are any markers in the text before processing
  if (!hasAnyMarkers(text)) return text;
  
  let result = text;
  
  // Apply all registered handlers
  for (const handler of markerHandlers) {
    if (handler.detect(result)) {
      result = handler.process(result);
    }
  }
  
  return result;
}

/**
 * Check if text contains any known markers
 */
export function hasAnyMarkers(text: string): boolean {
  if (!text) return false;
  
  // Check if any registered handler detects markers
  return markerHandlers.some(handler => handler.detect(text));
}

/**
 * Check if URL contains any known image markers
 */
export function hasAnyImageMarkers(url: string): boolean {
  if (!url) return false;
  
  // Check if any registered handler detects markers
  return imageMarkerHandlers.some(handler => handler.detect(url));
}

/**
 * Process blur effect markers
 */
export function processBlurMarkers(text: string): string {
  if (!text.includes(BLUR_START)) return text;
  
  // Pattern: __BLUR_START__content__BLUR_END__
  // Using [\s\S]*? for non-greedy multiline matching
  const blurRegex = new RegExp(`${BLUR_START}([\\s\\S]*?)${BLUR_END}`, 'g');
  
  return text.replace(blurRegex, (_match, content) => {
    console.log("DIY-MOD: Processing blur marker in utility");
    return `<span class="${CSS_CLASSES.BLUR}">${content}</span>`;
  });
}

/**
 * Process overlay effect markers
 */
export function processOverlayMarkers(text: string): string {
  if (!text.includes(OVERLAY_START)) return text;
  
  // Pattern: __OVERLAY_START__warning|content__OVERLAY_END__
  const overlayRegex = new RegExp(`${OVERLAY_START}(.*?)\\|([\\s\\S]*?)${OVERLAY_END}`, 'g');
  
  return text.replace(overlayRegex, (_match, warning, content) => {
    const warningText = warning.trim() || 'Content filtered';
    console.log(`DIY-MOD: Processing overlay marker with warning: ${warningText}`);
    return `<div class="${CSS_CLASSES.CONTENT_OVERLAY} ${CSS_CLASSES.OVERLAY} ${CSS_CLASSES.HIDDEN}" data-warning="${warningText}" onclick="this.classList.toggle('${CSS_CLASSES.HIDDEN}')">
      <div class="content">${content}</div>
      <div class="warning">${warningText}</div>
    </div>`;
  });
}

/**
 * Process rewrite effect markers
 */
export function processRewriteMarkers(text: string): string {
  if (!text.includes(REWRITE_START)) return text;
  
  // Pattern: __REWRITE_START__content__REWRITE_END__
  const rewriteRegex = new RegExp(`${REWRITE_START}([\\s\\S]*?)${REWRITE_END}`, 'g');
  
  return text.replace(rewriteRegex, (_match, content) => {
    console.log("DIY-MOD: Processing rewrite marker in utility");
    return `<div class="${CSS_CLASSES.REWRITTEN}">
      ${content}
      <div class="modification-indicator">Modified by DIY-MOD</div>
    </div>`;
  });
}




/**
 * Process image element with intervention configuration
 * @param imgElement The HTML image element to process
 * @param config The intervention configuration from DIY_IMG_ATTR
 */
export function processMarkedImage(imgElement: HTMLImageElement): void {
  if (!imgElement) return;

  const config=imgElement.getAttribute(DIY_IMG_ATTR);
  if (!config) return;
  console.log("DIY-MOD: Processing image with config:", config);
  
  // Parse the configuration and determine which intervention to apply
  try {
    const configData = JSON.parse(config);
    
    // Apply the appropriate handler based on the intervention type
    if (configData.type === 'overlay') {
      processOverlayImageMarker(imgElement, configData);
    } else if (configData.type === 'blur') {
      processBlurImageMarkers(imgElement, configData);
    } else if (configData.type === 'processed') {
      processStandardImageMarker(imgElement, configData);
    } else if (configData.type === 'cartoonish' || configData.type === 'edit') {
      // Handle cartoonish image processing
      processCartoonishImageMarker(imgElement, configData);
    } else {
      console.warn("DIY-MOD: Unknown image intervention type:", configData.type);
    }
    
    // Only remove the attribute for non-deferred processing
    // For deferred processing we'll remove it when complete
    if (configData.type !== 'cartoonish' || 
        (configData.type === 'cartoonish' && configData.status !== 'DEFERRED')) {
      // Remove the attribute after successfully processing to prevent reprocessing in future scans
      imgElement.removeAttribute(DIY_IMG_ATTR);
      
      // Add a data attribute to indicate this image has been processed
      imgElement.setAttribute('data-diy-mod-processed', 'true');
    }
    
  } catch (error) {
    console.error("DIY-MOD: Failed to parse image intervention config:", error);
  }
}




/**
 * Process standard image marker
 * @param imgElement The HTML image element to process
 * @param config The configuration containing processed image data
 */
export function processStandardImageMarker(imgElement: HTMLImageElement, config: any): void {
  if (!imgElement || !config) return;
  
  // Check if we have a URL to replace the image source with
  if (config.processed_image_url) {
    console.log("DIY-MOD: Processing standard image marker with URL:", config.processed_image_url);
    imgElement.src = config.processed_image_url;
    
    // Add a class to indicate this image has been processed
    imgElement.classList.add("diymod-processed-image");
    
    // Add any additional attributes if needed
    if (config.alt) {
      imgElement.alt = config.alt;
    }
  }
}

export function processBlurImageMarkers(imgElement: HTMLImageElement, config: any): void {
  if (!imgElement || !config || !config.coordinates || !Array.isArray(config.coordinates)) return;
  
  try {
    // Process each set of coordinates in the configuration
    console.log(`DIY-MOD: Processing blur image marker with ${config.coordinates.length} boxes`);
    
    // Loop through each box coordinate and apply overlays
    config.coordinates.forEach((box: { x1: number, y1: number, x2: number, y2: number }, index: number) => {
      // Extract coordinates from this box
      const { x1, y1, x2, y2 } = box;
      
      // Calculate dimensions
      let left = x1;
      let top = y1; // Use y1 for top position
      let width = (Number(x2) - Number(x1)).toString();
      let height = (Number(y2) - Number(y1)).toString();
      
      console.log(`DIY-MOD: Processing box ${index}: left=${left}, top=${top}, width=${width}, height=${height}`);
      
      // Use the existing applyOverlayToImage function to apply the overlay
      // We convert the coordinates to a string format that the function expects
      const blurInfo = [left, top, width, height].join('_');
      applyBlurToImage(imgElement, blurInfo);
    });
    
    // Add a class to indicate this image has been processed with an overlay
    imgElement.classList.add("diymod-blur-processed");
  }
 catch (error) {
    console.error("DIY-MOD: Error processing blur image marker:", error);
  }
}

/**
 * Process overlay image marker using the configuration
 * @param imgElement The HTML image element to process
 * @param config The configuration containing overlay coordinates
 */
export function processOverlayImageMarker(imgElement: HTMLImageElement, config: any): void {
  if (!imgElement || !config || !config.coordinates || !Array.isArray(config.coordinates)) return;
  
  try {
    // Process each set of coordinates in the configuration
    console.log(`DIY-MOD: Processing overlay image marker with ${config.coordinates.length} boxes`);
    
    // Loop through each box coordinate and apply overlays
    config.coordinates.forEach((box: { x1: number, y1: number, x2: number, y2: number }, index: number) => {
      // Extract coordinates from this box
      const { x1, y1, x2, y2 } = box;
      
      // Calculate dimensions
      let left = x1;
      let top = y1; // Use y1 for top position
      let width = (Number(x2) - Number(x1)).toString();
      let height = (Number(y2) - Number(y1)).toString();
      
      console.log(`DIY-MOD: Processing box ${index}: left=${left}, top=${top}, width=${width}, height=${height}`);
      
      // Use the existing applyOverlayToImage function to apply the overlay
      // We convert the coordinates to a string format that the function expects
      const overlayInfo = [left, top, width, height].join('_');
      applyOverlayToImage(imgElement, overlayInfo);
    });
    
    // Add a class to indicate this image has been processed with an overlay
    imgElement.classList.add("diymod-overlay-processed");
  }
 catch (error) {
    console.error("DIY-MOD: Error processing overlay image marker:", error);
  }
}

/**
 * Apply overlay to an image element directly in the DOM
 * This is called by the DOM processor after the image is in the DOM
 */
export function applyOverlayToImage(img: HTMLImageElement, overlayInfo: string): void {
  try {
    // Parse overlay information
    const [left, top, width, height] = overlayInfo.split('_').map(Number);
    const overlayUrl = "https://tinypng.com/images/social/website.jpg"; // Static overlay image
    
    // Wrap the image in a container if it's not already wrapped in one with the expected class
    let container;
    if (img.parentElement && img.parentElement.classList.contains("diymod-image-container")) {
      container = img.parentElement;
    } else {
      container = document.createElement("div");
      container.className = "diymod-image-container";
      container.style.display = "inline-block";
      container.style.position = "relative";
      
      // Insert the container before the image and move the image inside of it
      if (img.parentNode) {
        img.parentNode.insertBefore(container, img);
        container.appendChild(img);
      }
    }
    
    // Check if we already have an overlay with the same parameters
    const existingOverlay = Array.from(container.querySelectorAll('img')).find(overlay => 
      overlay !== img && 
      overlay.style.left === `${left}px` && 
      overlay.style.top === `${top}px` && 
      overlay.style.width === `${width}px` && 
      overlay.style.height === `${height}px`
    );
    
    // Only create a new overlay if we don't have one with the same parameters
    if (!existingOverlay) {
      // Create an overlay element
      const overlay = document.createElement("img");
      overlay.src = overlayUrl;
      overlay.style.position = "absolute";
      overlay.style.left = `${left}px`;
      overlay.style.top = `${top}px`;
      overlay.style.width = `${width}px`;
      overlay.style.height = `${height}px`;
      overlay.style.pointerEvents = "none";  // Allow clicks to pass through if needed
      overlay.classList.add("diymod-overlay-image");
      
      // Append the overlay element to the container
      container.appendChild(overlay);
      
      console.log(`DIY-MOD: Overlay applied on image`);
    }
  } catch (error) {
    console.error('DIY-MOD: Error applying overlay to image:', error);
  }
}

/**
 * Process cartoonish image marker with deferred processing
 * @param imgElement The HTML image element to process
 * @param config The configuration containing processing status and filters
 */
export function processCartoonishImageMarker(imgElement: HTMLImageElement, config: any): void {
  if (!imgElement || !config) return;
  
  try {
    console.log("DIY-MOD: Processing cartoonish image marker:", config);
    
    // Check the status of the cartoonish image processing
    if (config.status === "DEFERRED") {
      // Show a loading state for the image
      showImageLoadingState(imgElement);
      
      // Start polling for the completed image
      const originalUrl = imgElement.src;
      
      // Use best_filter_name if available, otherwise fall back to filters array
      // This ensures we poll with the exact filter that was used for processing
      const pollingFilters = config.best_filter_name ? [config.best_filter_name] : (config.filters || []);
      
      console.log("DIY-MOD: Starting polling with filters:", pollingFilters);
      
      startImagePolling(imgElement, originalUrl, pollingFilters, config);
    } else if (config.status === "COMPLETED" && config.processedUrl) {
      // If the process is already completed, just set the image
      imgElement.src = config.processedUrl;
      imgElement.classList.add("diymod-cartoonish-processed");
      
      // Remove any loading indicators
      removeImageLoadingState(imgElement);
    }
  } catch (error) {
    console.error("DIY-MOD: Error processing cartoonish image marker:", error);
    removeImageLoadingState(imgElement);
  }
}

/**
 * Show a loading state on an image while it's being processed
 * @param imgElement The image element to show loading state for
 */
function showImageLoadingState(imgElement: HTMLImageElement): void {
  // Create a container for the image if it doesn't exist
  let container = imgElement.parentElement;
  if (!container || !container.classList.contains("diymod-image-container")) {
    container = document.createElement("div");
    container.className = "diymod-image-container";
    container.style.display = "inline-block";
    container.style.position = "relative";
    
    // Insert the container before the image and move the image inside of it
    if (imgElement.parentNode) {
      imgElement.parentNode.insertBefore(container, imgElement);
      container.appendChild(imgElement);
    }
  }
  
  // Add processing class to the image
  imgElement.classList.add(CSS_CLASSES.PROCESSING);
  
  // Add a loading indicator
  const loadingIndicator = document.createElement("div");
  loadingIndicator.className = "diymod-loading-indicator";
  loadingIndicator.innerHTML = `
    <div class="loading-spinner"></div>
    <div class="loading-text">Transforming image...</div>
  `;
  loadingIndicator.style.position = "absolute";
  loadingIndicator.style.top = "0";
  loadingIndicator.style.left = "0";
  loadingIndicator.style.width = "100%";
  loadingIndicator.style.height = "100%";
  loadingIndicator.style.display = "flex";
  loadingIndicator.style.flexDirection = "column";
  loadingIndicator.style.alignItems = "center";
  loadingIndicator.style.justifyContent = "center";
  loadingIndicator.style.backgroundColor = "rgba(0, 0, 0, 0.6)";
  loadingIndicator.style.color = "white";
  loadingIndicator.style.zIndex = "1000";
  
  container.appendChild(loadingIndicator);
}

/**
 * Remove the loading state from an image
 * @param imgElement The image element to remove loading state from
 */
function removeImageLoadingState(imgElement: HTMLImageElement): void {
  // Remove the processing class
  imgElement.classList.remove(CSS_CLASSES.PROCESSING);
  
  // Remove the loading indicator if it exists
  const container = imgElement.parentElement;
  if (container) {
    const loadingIndicator = container.querySelector(".diymod-loading-indicator");
    if (loadingIndicator) {
      container.removeChild(loadingIndicator);
    }
  }
}

/**
 * Start polling for a processed image
 * @param imgElement The image element to update when processing is complete
 * @param originalUrl The original URL of the image
 * @param filters The filters applied to the image
 * @param config The original configuration
 */
function startImagePolling(
  imgElement: HTMLImageElement, 
  originalUrl: string, 
  filters: string[], 
  imgConfig: any
): void {
  // Use the best_filter_name for polling if available, otherwise fall back to filters
  // This ensures we poll using the exact filter that matched during processing
  const pollingFilters = imgConfig.best_filter_name ? [imgConfig.best_filter_name] : filters;
  
  // Create a unique key for this image using the correct filter
  const key = `${originalUrl}-${JSON.stringify(pollingFilters)}`;
  
  // Default polling parameters - don't rely directly on config which might not be fully loaded
  const DEFAULT_MAX_ATTEMPTS = 20;
  
  // Get max attempts from config if available, otherwise use default
  const maxPollAttempts = config?.api?.polling?.maxAttempts || DEFAULT_MAX_ATTEMPTS;
  
  // Track this deferred image processing
  const deferredImage: DeferredImageProcessing = {
    imageElement: imgElement,
    originalUrl: originalUrl,
    filters: pollingFilters,  // Use the corrected filters for polling
    config: imgConfig,
    pollCount: 0,
    maxPolls: maxPollAttempts
  };
  
  // Store in the tracking map
  deferredImages.set(key, deferredImage);
  
  // Start polling
  pollForImageResult(key);
}

/**
 * Poll the server for an image processing result
 * @param key The unique key for the deferred image
 */
function pollForImageResult(key: string): void {
  const deferredImage = deferredImages.get(key);
  if (!deferredImage) return;
  
  // Check if we've reached max polling attempts
  if (deferredImage.pollCount >= deferredImage.maxPolls) {
    console.log(`DIY-MOD: Reached max polling attempts for image ${key}`);
    removeImageLoadingState(deferredImage.imageElement);
    deferredImages.delete(key);
    return;
  }
  
  // Increment poll count
  deferredImage.pollCount++;
  
  // Create a unique request ID for this polling request
  const requestId = `poll_${key}_${Date.now()}`;
  
  let timeoutId: any;

  // Set up one-time listener for the response
  const messageHandler = (event: MessageEvent) => {
    if (event.source !== window) return;
    if (event.data.type !== 'diymod_poll_image_response') return;
    if (event.data.requestId !== requestId) return;

    // A response was received, so we can clear the timeout
    clearTimeout(timeoutId);
    
    // Clean up listener
    window.removeEventListener('message', messageHandler);
    
    const response = event.data.response;
    
    if (!response || !response.success) {
      console.error(`DIY-MOD: Error polling for image ${key}:`, response?.error || 'No response');
      scheduleNextPoll(key);
      return;
    }
    
    const data = response.result;
    console.log(`DIY-MOD: Poll ${deferredImage.pollCount} result for ${key}:`, data);
    
    if (data.status === "COMPLETED" && data.processed_value) {
      // Update the image with the processed URL
      deferredImage.imageElement.src = data.processed_value;
      deferredImage.imageElement.classList.add("diymod-cartoonish-processed");
      
      // Remove loading state
      removeImageLoadingState(deferredImage.imageElement);
      
      // Remove from tracking
      deferredImages.delete(key);
    } else if (data.status === "NOT FOUND") {
      scheduleNextPoll(key);
    } else {
      scheduleNextPoll(key);
    }
  };
  
  // Add the listener for the response
  window.addEventListener('message', messageHandler);
  
  // Send the request through the bridge
  window.postMessage({
    type: 'diymod_poll_image_request',
    requestId,
    imageUrl: deferredImage.originalUrl,
    filters: deferredImage.filters
  }, '*');
  
  // Set a timeout to handle cases where no response is received
  timeoutId = setTimeout(() => {
    // The listener will be removed by the timeout itself, so no need to remove it again here.
    // The main purpose is to log an error and try polling again.
    console.error(`DIY-MOD: No response received for polling request ${requestId}`);
    // Make sure to remove the listener to avoid memory leaks if the timeout fires
    window.removeEventListener('message', messageHandler);
    scheduleNextPoll(key);
  }, 5000); // 5 second timeout
  
  // Helper function to schedule the next poll with proper interval
  function scheduleNextPoll(pollKey: string) {
    // Default polling interval - don't rely directly on config which might not be fully loaded 
    const DEFAULT_POLLING_INTERVAL_MS = 8000;
    
    // Get interval from config if available, otherwise use default
    const pollingIntervalMs = config?.api?.polling?.intervalMs || DEFAULT_POLLING_INTERVAL_MS;
    
    setTimeout(() => {
      pollForImageResult(pollKey);
    }, pollingIntervalMs);
  }
}

/**
 * Apply a blur overlay to a specific rectangular region of an image.
 * @param img The image element to blur a region of.
 * @param blurInfo A string "left_top_width_height".
 */
export function applyBlurToImage(img: HTMLImageElement, blurInfo: string): void {
  try {
    const [left, top, width, height] = blurInfo.split('_').map(Number);
    // Ensure container
    let container: HTMLElement;
    if (img.parentElement?.classList.contains('diymod-image-container')) {
      container = img.parentElement as HTMLElement;
    } else {
      container = document.createElement('div');
      container.className = 'diymod-image-container';
      container.style.display = 'inline-block';
      container.style.position = 'relative';
      if (img.parentNode) {
        img.parentNode.insertBefore(container, img);
        container.appendChild(img);
      }
    }
    // Avoid duplicate blur overlays
    const existing = Array.from(container.querySelectorAll('.diymod-blur-overlay'))
      .find(el => {
        const rect = (el as HTMLElement).getBoundingClientRect();
        return rect.left === left && rect.top === top &&
               rect.width === width && rect.height === height;
      });
    if (!existing) {
      const overlay = document.createElement('div');
      overlay.className = 'diymod-blur-overlay';
      Object.assign(overlay.style, {
        position: 'absolute',
        left: `${left}px`,
        top: `${top}px`,
        width: `${width}px`,
        height: `${height}px`,
        backdropFilter: 'blur(8px)',
        pointerEvents: 'none'
      });
      container.appendChild(overlay);
      console.log('DIY-MOD: Blur overlay applied to image');
    }
  } catch (error) {
    console.error('DIY-MOD: Error applying blur to image:', error);
  }
}

// Register built-in text markers
registerMarkerHandler({
  name: 'blur',
  startMarker: BLUR_START,
  endMarker: BLUR_END,
  detect: (text) => text.includes(BLUR_START),
  process: processBlurMarkers
});

registerMarkerHandler({
  name: 'overlay',
  startMarker: OVERLAY_START,
  endMarker: OVERLAY_END,
  detect: (text) => text.includes(OVERLAY_START),
  process: processOverlayMarkers
});

registerMarkerHandler({
  name: 'rewrite',
  startMarker: REWRITE_START,
  endMarker: REWRITE_END,
  detect: (text) => text.includes(REWRITE_START),
  process: processRewriteMarkers
});

// // Register built-in image markers
// registerImageMarkerHandler({
//   name: 'processed_image',
//   marker: MARKERS.PROCESSED_IMAGE,
//   detect: (url) => url.includes(MARKERS.PROCESSED_IMAGE),
//   process: processStandardImageMarker
// });

// // Register overlay image marker
// registerImageMarkerHandler({
//   name: 'overlay_image',
//   marker: MARKERS.OVERLAY_IMAGE,
//   detect: (url) => url.includes(MARKERS.OVERLAY_IMAGE),
//   process: processOverlayImageMarker
// });