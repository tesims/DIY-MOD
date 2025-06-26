# 🧪 DIY-MOD Extension Testing Guide

## **Current System Status** ✅

- **Server**: Running with API keys fixed
- **WebSocket**: Working (`ws://localhost:5001/ws/{user_id}`)
- **HTTP Endpoints**: Working (`http://localhost:5001/ping`)
- **Extension**: Built with WebSocket support

---

## **Step 1: Install the Extension**

### Load Extension in Chrome:
1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select: `DIY_Mod/BrowserExtension/modernized-extension/dist/`
5. Extension should appear in the extensions list

### Verify Installation:
- Extension icon should appear in Chrome toolbar
- Click the extension icon to open popup
- Should show "DIY-MOD Content Moderation" interface

---

## **Step 2: Test WebSocket Connection**

### Using the Test Page:
1. Open: `file:///Users/academics/summer-projects/diy-mod/DIY_Mod/test-extension.html`
2. Click "Test Server Connection" → Should be ✅ Green
3. Click "Test WebSocket Connection" → Should be ✅ Green  
4. Click "Test Extension Injection" → Should be ⚠️ Warning (expected, no extension on file:// pages)

### Expected Results:
```
✅ Server connected and responding
✅ WebSocket connection working  
⚠️ Extension may not be installed or enabled
```

---

## **Step 3: Test on Real Social Media**

### Reddit Testing:
1. Go to: `https://www.reddit.com/r/PlasticSurgery` (or any Reddit page)
2. Open Chrome DevTools (F12) → Console tab
3. Look for DIY-MOD messages:
   ```
   DIY-MOD: Successfully connected to API server at http://localhost:5001
   DIY-MOD: WebSocket connected for user {user_id}
   DIY-MOD: Processing feed via WebSocket...
   ```

### Twitter/X Testing:
1. Go to: `https://x.com/home` (or `https://twitter.com/home`)
2. Open Chrome DevTools → Console tab
3. Look for similar DIY-MOD messages

---

## **Step 4: Monitor WebSocket Communication**

### Server Logs:
```bash
ssh -i ~/Downloads/rayhan-keypair.pem ubuntu@13.58.180.224 "tail -f /opt/DIY-MOD/Backend/debug.log | grep -E 'WebSocket|ws/'"
```

### Expected WebSocket Log Messages:
```
INFO: WebSocket /ws/{user_id} [accepted]
INFO: WebSocket connected for user {user_id}  
INFO: Processing feed via WebSocket for user {user_id}
INFO: WebSocket processing completed successfully
```

---

## **Step 5: Test Content Processing**

### Look for Processed Content:
1. **Text Rewriting**: Posts should show modified text with `__REWRITE_START__` and `__REWRITE_END__` markers
2. **Image Processing**: Images should have overlay/blur effects applied
3. **Performance**: Processing should be faster than HTTP polling

### Browser Network Tab:
1. Open DevTools → Network tab
2. Should see **WebSocket connections** instead of repeated HTTP POST requests
3. WebSocket connection should persist across page navigation

---

## **Troubleshooting Guide**

### If Extension Not Loading:
```bash
cd BrowserExtension/modernized-extension
npm run build
```
Then reload extension in Chrome.

### If WebSocket Not Connecting:
1. Check server is running: `curl http://localhost:5001/ping`
2. Check SSH tunnel: `lsof -i :5001`
3. Restart server: `./start_server_with_env.sh`

### If No Content Processing:
1. Check API keys in server logs
2. Verify user filters are set up
3. Check browser console for JavaScript errors

---

## **Performance Comparison**

### Before (HTTP Polling):
- **Request Type**: HTTP POST to `/get_feed` every few seconds
- **Connection**: New connection per request
- **Latency**: Higher due to request/response overhead

### After (WebSocket):
- **Connection Type**: Persistent WebSocket connection
- **Communication**: Real-time bidirectional
- **Latency**: Lower, instant processing

---

## **Success Indicators**

### ✅ Extension Working Correctly:
1. Console shows WebSocket connection established
2. Feed processing happens via WebSocket (not HTTP)
3. Content is filtered/rewritten in real-time
4. No polling HTTP requests in Network tab

### ✅ Performance Improvements:
1. Faster initial page load processing
2. Reduced server load (no polling)
3. Real-time content updates

---

## **Quick Test Commands**

```bash
# Test server status
curl http://localhost:5001/ping

# Test WebSocket manually
wscat -c ws://localhost:5001/ws/test_user

# Check server logs
ssh -i ~/Downloads/rayhan-keypair.pem ubuntu@13.58.180.224 "tail -20 /opt/DIY-MOD/Backend/debug.log"

# Rebuild extension
cd BrowserExtension/modernized-extension && npm run build
```

---

## **Next Steps**

1. **Install Extension** → Load in Chrome from `dist/` folder
2. **Test on Reddit** → Go to r/PlasticSurgery and check console
3. **Monitor Logs** → Watch for WebSocket messages
4. **Verify Performance** → No HTTP polling, faster processing

The WebSocket implementation is now ready for testing! 🚀 