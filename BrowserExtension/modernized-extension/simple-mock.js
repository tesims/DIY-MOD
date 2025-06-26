import express from 'express';
import cors from 'cors';

const app = express();
const PORT = 5001;

// Middleware
app.use(cors());
app.use(express.json());

// Simple ping endpoint
app.get('/ping', (req, res) => {
    console.log('🏓 Ping received');
    res.json({ 
        status: 'ok', 
        message: 'Mock server is running', 
        timestamp: new Date().toISOString() 
    });
});

// Health check
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        message: 'DIY Mod Simple Mock Server'
    });
});

// Mock feed processing endpoint
app.post('/get_feed', (req, res) => {
    console.log('📡 HTTP feed processing request');
    res.json({
        feed: {
            response: req.body.response || '<div>Mock processed content</div>',
            processed: true,
            timestamp: new Date().toISOString()
        }
    });
});

app.listen(PORT, () => {
    console.log(`
🚀 Simple Mock Server Running
============================
📡 Server: http://localhost:${PORT}
🏓 Ping: http://localhost:${PORT}/ping
📊 Health: http://localhost:${PORT}/health

Ready for testing!
    `);
}); 