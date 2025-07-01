# DIY Content Moderation - Render Deployment Guide

This guide will help you deploy the DIY Content Moderation system to Render, replacing the problematic EC2 setup.

## Prerequisites

1. **Render Account**: Sign up at [render.com](https://render.com)
2. **GitHub Repository**: Your code should be in a GitHub repository
3. **API Keys**: Get your API keys ready (but don't commit them!)

## Step 1: Prepare Your API Keys

You'll need these API keys:

### Google AI Studio API Key
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Copy the key (starts with `AIzaSy...`)

### OpenAI API Key  
1. Go to [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Create a new secret key
3. Copy the key (starts with `sk-proj-...`)

## Step 2: Deploy to Render

### Option A: Automatic Deployment (Recommended)
1. Fork or push your code to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Render will detect the `render.yaml` file and auto-configure

### Option B: Manual Setup
1. In Render Dashboard, click "New +" → "Web Service"
2. Connect your GitHub repository
3. Configure these settings:
   - **Name**: `diy-content-moderation`
   - **Runtime**: `Python 3`
   - **Build Command**: `cd Backend && pip install -r requirements.txt`
   - **Start Command**: `cd Backend && uvicorn fastapi_app:app --host 0.0.0.0 --port $PORT`
   - **Auto-Deploy**: `Yes`

## Step 3: Set Environment Variables

In your Render service settings, add these environment variables:

```
GOOGLE_API_KEY=your_actual_google_api_key_here
OPENAI_API_KEY=your_actual_openai_api_key_here
LLM_PROVIDER=gemini
PRIMARY_MODEL=gemini-2.0-flash
FALLBACK_MODEL=gpt-4o-mini
USE_GEMINI_FOR_VISION=true
USE_GEMINI_FOR_TEXT=true
```

### How to Add Environment Variables:
1. Go to your service in Render Dashboard
2. Click "Environment" tab
3. Click "Add Environment Variable"
4. Add each variable one by one
5. Click "Save Changes"

## Step 4: Update Browser Extension

Once deployed, update your browser extension to use the new Render URL:

1. Get your Render service URL (e.g., `https://diy-content-moderation.onrender.com`)
2. Update the extension's backend URL configuration
3. Test with `/ping` endpoint: `https://your-app.onrender.com/ping`

## Step 5: Test the Deployment

### Health Check
```bash
curl https://your-app.onrender.com/ping
```

### API Test
```bash
curl -X POST https://your-app.onrender.com/get_feed \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "url": "https://reddit.com",
    "data": "{\"feed_info\": {\"response\": \"test data\"}}"
  }'
```

## Step 6: Update Extension Configuration

Update your browser extension's `manifest.json` or configuration to point to your new Render URL:

```javascript
// Replace the old EC2 URL with your Render URL
const BACKEND_URL = 'https://your-app.onrender.com';
```

## Troubleshooting

### Common Issues

1. **Build Fails**: Check that `requirements.txt` is properly formatted
2. **API Key Errors**: Verify environment variables are set correctly
3. **Port Issues**: Render automatically sets the PORT variable
4. **Timeout Issues**: Upgrade to a paid plan if using heavy ML models

### Logs
- View logs in Render Dashboard under "Logs" tab
- Check for API key validation errors
- Monitor for import/dependency issues

### Performance Optimization

1. **Upgrade Plan**: Free tier has limitations - consider Starter ($7/month) or Standard ($25/month)
2. **Enable Auto-Deploy**: For automatic updates when you push to GitHub
3. **Set up Health Checks**: The `/ping` endpoint is already configured

## Benefits of Render vs EC2

✅ **Automatic HTTPS/SSL**
✅ **Auto-scaling**  
✅ **Integrated CI/CD**
✅ **Managed infrastructure**
✅ **Built-in monitoring**
✅ **No SSH/server management**
✅ **Environment variable management**
✅ **Zero-downtime deployments**

## Migration Checklist

- [ ] Repository pushed to GitHub
- [ ] API keys obtained
- [ ] Render service created
- [ ] Environment variables set
- [ ] Deployment successful
- [ ] Health check passing
- [ ] Browser extension updated
- [ ] End-to-end testing completed
- [ ] Old EC2 instance terminated

## Support

If you encounter issues:
1. Check Render logs first
2. Verify all environment variables are set
3. Test API endpoints manually
4. Check GitHub repository connectivity

Your DIY Content Moderation system should now be running reliably on Render! 🚀 