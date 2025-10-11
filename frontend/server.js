const express = require('express');
const path = require('path');
const { t } = require('./public/js/translations');
require('dotenv').config();

const app = express();
const PORT = process.env.FRONTEND_PORT || 3000;
const API_URL = process.env.API_URL || 'http://localhost:5001';

// Set view engine
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// Serve static files
app.use(express.static(path.join(__dirname, 'public')));

// Routes
app.get('/', (req, res) => {
    res.render('index', {
        title: 'WeRadio - HLS Live Streaming',
        t: t,
        apiUrl: API_URL
    });
});

// Start server
app.listen(PORT, () => {
    console.log(`Frontend server running on ${API_URL}`);
});