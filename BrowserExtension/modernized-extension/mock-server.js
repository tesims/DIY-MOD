import express from 'express';
import { WebSocketServer } from 'ws';
import http from 'http';
import cors from 'cors';

const app = express();
const server = http.createServer(app);
const wss = new WebSocketServer({ server, path: '/ws' });

// Middleware
app.use(cors());
app.use(express.json());

// Store for active WebSocket connections
const connections = new Map();

// WebSocket connection handling
wss.on('connection', (ws, req) => {
    console.log('🔌 New WebSocket connection established');
    
    // Extract user_id from URL path (e.g., /ws/user123)
    const urlParts = req.url.split('/');
    const userId = urlParts[urlParts.length - 1] || 'default_user';
    
    connections.set(userId, ws);
    
    // Send connection acknowledgment
    ws.send(JSON.stringify({
        type: 'connection_ack',
        message: 'WebSocket connection established',
        userId: userId
    }));
    
    ws.on('message', async (data) => {
        try {
            const message = JSON.parse(data.toString());
            console.log('📨 Received WebSocket message:', message.type);
            
            if (message.type === 'process_feed') {
                // Simulate feed processing
                const response = await simulateProcessing(message.data);
                
                ws.send(JSON.stringify({
                    type: 'processing_response',
                    requestId: message.requestId,
                    data: response
                }));
            }
        } catch (error) {
            console.error('❌ Error processing WebSocket message:', error);
            ws.send(JSON.stringify({
                type: 'error',
                message: 'Error processing request',
                error: error.message
            }));
        }
    });
    
    ws.on('close', () => {
        console.log('🔌 WebSocket connection closed for user:', userId);
        connections.delete(userId);
    });
    
    ws.on('error', (error) => {
        console.error('❌ WebSocket error:', error);
    });
});

// Simulate processing with mock data
async function simulateProcessing(data) {
    console.log('⚙️ Simulating feed processing for:', data.platform);
    
    // Simulate processing delay
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Mock processed HTML with some text replacements
    let processedHtml = data.response || '<div>Mock processed content</div>';
    
    // Simulate content filtering/processing
    if (data.platform === 'reddit') {
        processedHtml = processedHtml.replace(/Trump/gi, '**FILTERED**');
        processedHtml = processedHtml.replace(/politics/gi, '**FILTERED**');
    } else if (data.platform === 'twitter') {
        processedHtml = processedHtml.replace(/weight loss/gi, '**FILTERED**');
        processedHtml = processedHtml.replace(/surgery/gi, '**FILTERED**');
    }
    
    return {
        feed: {
            response: processedHtml,
            processed: true,
            timestamp: new Date().toISOString(),
            platform: data.platform,
            userId: data.userId
        }
    };
}

// HTTP endpoints for compatibility
app.get('/ping', (req, res) => {
    console.log('🏓 Ping received');
    res.json({ status: 'ok', message: 'Mock server is running', timestamp: new Date().toISOString() });
});

app.post('/get_feed', async (req, res) => {
    console.log('📡 HTTP feed processing request (fallback)');
    try {
        const response = await simulateProcessing(req.body);
        res.json(response);
    } catch (error) {
        console.error('❌ Error processing HTTP request:', error);
        res.status(500).json({ error: error.message });
    }
});

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        connections: connections.size,
        timestamp: new Date().toISOString(),
        message: 'DIY Mod Mock Server - WebSocket Ready'
    });
});

const PORT = process.env.PORT || 5001;

server.listen(PORT, () => {
    console.log(`
🚀 DIY Mod Mock Server Starting
================================
📡 HTTP Server: http://localhost:${PORT}
🔌 WebSocket Server: ws://localhost:${PORT}/ws/{user_id}
📊 Health Check: http://localhost:${PORT}/health
🏓 Ping Endpoint: http://localhost:${PORT}/ping

✅ Ready for WebSocket testing!
    `);
});

// Graceful shutdown
process.on('SIGTERM', () => {
    console.log('🛑 Shutting down mock server...');
    server.close(() => {
        console.log('✅ Mock server shut down gracefully');
        process.exit(0);
    });
}); 