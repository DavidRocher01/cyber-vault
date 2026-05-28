const http = require('http');

// Use a no-keepalive agent so the proxy never pools connections.
// This prevents "socket hang up" races where a pooled connection is reused
// after the server (uvicorn) has already closed it between tests.
module.exports = {
  '/api': {
    target: 'http://localhost:8000',
    secure: false,
    changeOrigin: true,
    agent: new http.Agent({ keepAlive: false }),
  },
};
