# Extension Testing Guide

This guide provides step-by-step instructions for testing the DIY Content Moderation browser extension.

## Prerequisites

- Chrome browser
- Extension built and loaded
- Backend server running (EC2 recommended)

## Quick Test Setup

### 1. Build Extension
```bash
cd BrowserExtension/modernized-extension
npm run build
```

### 2. Load Extension in Chrome
1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top-right)
3. Click "Load unpacked"
4. Select folder: `BrowserExtension/modernized-extension/dist`
5. Extension should now appear in your extensions list

### 3. Connect to Backend Server

**Option A: EC2 Server (Recommended)**
```bash
ssh -i ~/Downloads/rayhan-keypair.pem -L 5001:localhost:5000 ubuntu@13.58.180.224 -N
```

**Option B: Local Development**
```bash
./start_local_system.sh
```

### 4. Configure Extension
Open browser console (F12) and set mode:
```javascript
// For EC2 server (recommended)
localStorage.setItem('diy_mod_dev_mode', 'false');

// For local development
localStorage.setItem('diy_mod_dev_mode', 'true');
```

## Testing Procedures

### Test 1: Reddit Processing
1. Navigate to: https://www.reddit.com/r/PlasticSurgery
2. Open browser console (F12)
3. Look for console messages:
   - "DIY-MOD: Successfully connected to API server"
   - "Processing feed request for user..."
   - "Successfully processed X/Y posts"

**Expected Results:**
- Posts with surgery/weight loss content should be processed
- Images should be analyzed and filtered
- Text content should be rewritten based on filters

### Test 2: Twitter/X Processing
1. Navigate to: https://x.com (Twitter)
2. Open browser console (F12)
3. Look for similar processing messages

**Expected Results:**
- Tweet processing with image analysis
- Content filtering and rewriting
- No errors in console

### Test 3: Filter Management
1. Click the DIY-MOD extension icon
2. Test filter creation and management
3. Verify filters are applied to content

## Console Monitoring

### Success Indicators
Look for these messages in browser console:
```
DIY-MOD: Successfully connected to API server at http://localhost:5001
Processing feed request for user [user_id] from [platform]
Successfully processed X/Y posts
Best filter for image [url]: [filter_name]
```

### Error Indicators
Watch for these errors:
```
DIY-MOD: API server at [url] is not responding
Failed to process feed: [error]
Error processing image: [error]
```

## Server Log Monitoring

If you have SSH access to the server, monitor logs:
```bash
ssh -i ~/Downloads/rayhan-keypair.pem ubuntu@13.58.180.224 "tail -f /opt/DIY-MOD/Backend/debug.log"
```

**Successful Processing Logs:**
- "Successfully processed X/Y posts"
- "Best filter for image [...]: weight loss or weight loss transformation"
- "HTTP 200 OK responses"
- "Parallel processing completed in Xs"

## Testing Scenarios

### Scenario 1: Weight Loss Content
1. Visit r/loseit or r/progresspics
2. Verify weight loss images are detected
3. Check that transformations are properly filtered

### Scenario 2: Surgery Content
1. Visit r/PlasticSurgery
2. Look for surgical procedure posts
3. Verify before/after images are processed

### Scenario 3: Mixed Content
1. Visit general subreddits with mixed content
2. Verify only relevant content is processed
3. Check that non-matching content passes through

## Performance Testing

### Metrics to Monitor
- Processing time per post (should be < 1 second)
- API response times
- Memory usage in browser
- Network requests in Developer Tools

### Load Testing
1. Scroll through multiple pages
2. Monitor processing consistency
3. Check for memory leaks or performance degradation

## Troubleshooting

### Extension Not Loading
```bash
# Rebuild extension
cd BrowserExtension/modernized-extension
npm run build

# Check for build errors
npm run build 2>&1 | grep -i error
```

### Connection Issues
```bash
# Test server connectivity
curl http://localhost:5001/ping

# Check tunnel status
ps aux | grep ssh | grep rayhan
```

### API Errors
Check for:
- Invalid API keys
- Rate limiting (503 errors)
- Network connectivity issues

## Test Results Documentation

### Success Criteria
- ✅ Extension loads without errors
- ✅ Backend connection established
- ✅ Reddit posts processed correctly
- ✅ Twitter/X posts processed correctly
- ✅ Image analysis working
- ✅ Text rewriting functional
- ✅ No console errors during normal operation

### Performance Benchmarks
Based on recent logs:
- Reddit processing: ~0.34s average per post
- Twitter processing: ~0.17s average per tweet
- Image processing: 200 OK responses
- Success rate: 95%+ (24/25 posts typically succeed)

## Known Issues

### SSH Tunnel Instability
- **Issue**: Connection refused errors
- **Workaround**: Restart tunnel connection
- **Command**: `pkill -f "ssh.*rayhan" && ssh -i ~/Downloads/rayhan-keypair.pem -L 5001:localhost:5000 ubuntu@13.58.180.224 -N &`

### API Rate Limiting
- **Issue**: 503 UNAVAILABLE errors
- **Solution**: Retry logic handles this automatically
- **Impact**: Minimal, most requests succeed on retry

### Local Development Import Conflicts
- **Issue**: Google GenAI import errors
- **Solution**: Use EC2 server instead
- **Status**: Local development not recommended

## Final Verification

Before considering testing complete:
1. Extension successfully loads and connects
2. Both Reddit and Twitter processing work
3. Image analysis returns meaningful results
4. Text content is appropriately filtered/rewritten
5. No critical errors in console logs
6. Performance is acceptable (< 1s per post)

The system is ready for production use when all success criteria are met. 