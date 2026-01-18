import socket
import threading
import os
import json
import mimetypes
from datetime import datetime
from urllib.parse import parse_qs, urlparse
import logging

# Configure logging (NO file logging for deployment)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Only console logging
    ]
)

class HTTPServer:
    """Advanced HTTP Server with multi-threading, routing, and middleware support"""
    
    def __init__(self, host='0.0.0.0', port=8080, max_connections=10):
        self.host = host
        self.port = port
        self.max_connections = max_connections
        self.routes = {}
        self.middleware = []
        self.static_dir = 'static'
        
        # Initialize socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Register default routes
        self._register_default_routes()
        
    def _register_default_routes(self):
        """Register default application routes"""
        self.route('GET', '/', self.serve_index)
        self.route('GET', '/book', self.serve_book)
        self.route('GET', '/api/stats', self.serve_stats)
        self.route('POST', '/api/book', self.update_book)
        
    def route(self, method, path, handler):
        """Register a route handler"""
        key = f"{method}:{path}"
        self.routes[key] = handler
        logging.info(f"Registered route: {method} {path}")
        
    def use(self, middleware_func):
        """Add middleware function"""
        self.middleware.append(middleware_func)
        
    def start(self):
        """Start the server"""
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(self.max_connections)
            logging.info(f'[STARTUP] Server running on http://{self.host}:{self.port}')
            
            while True:
                client_socket, client_address = self.server_socket.accept()
                logging.info(f'Connection from {client_address}')
                
                # Handle each client in a separate thread
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_address)
                )
                client_thread.daemon = True
                client_thread.start()
                
        except KeyboardInterrupt:
            logging.info('\n[SHUTDOWN] Server shutting down...')
        except Exception as e:
            logging.error(f'Server error: {e}')
        finally:
            self.server_socket.close()
            
    def _handle_client(self, client_socket, client_address):
        """Handle individual client connection"""
        try:
            # Receive request with timeout
            client_socket.settimeout(5.0)
            request_data = client_socket.recv(4096).decode('utf-8')
            
            if not request_data:
                return
                
            # Parse request
            request = self._parse_request(request_data)
            request['client_address'] = client_address
            
            # Apply middleware
            for middleware_func in self.middleware:
                request = middleware_func(request)
                if request.get('response'):
                    # Middleware returned early response
                    self._send_response(client_socket, request['response'])
                    return
            
            # Route request
            response = self._route_request(request)
            
            # Send response
            self._send_response(client_socket, response)
            
        except socket.timeout:
            logging.warning(f'Request timeout from {client_address}')
        except Exception as e:
            logging.error(f'Error handling client {client_address}: {e}')
            error_response = self._create_response(500, 'Internal Server Error')
            self._send_response(client_socket, error_response)
        finally:
            client_socket.close()
            
    def _parse_request(self, request_data):
        """Parse HTTP request into structured format"""
        lines = request_data.split('\r\n')
        
        # Parse request line
        request_line = lines[0].split()
        method = request_line[0] if len(request_line) > 0 else 'GET'
        full_path = request_line[1] if len(request_line) > 1 else '/'
        protocol = request_line[2] if len(request_line) > 2 else 'HTTP/1.1'
        
        # Parse URL and query parameters
        parsed_url = urlparse(full_path)
        path = parsed_url.path
        query_params = parse_qs(parsed_url.query)
        
        # Parse headers
        headers = {}
        body = ''
        body_start = False
        
        for line in lines[1:]:
            if line == '':
                body_start = True
                continue
            if body_start:
                body += line + '\r\n'
            else:
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()
        
        return {
            'method': method,
            'path': path,
            'protocol': protocol,
            'headers': headers,
            'query_params': query_params,
            'body': body.strip()
        }
        
    def _route_request(self, request):
        """Route request to appropriate handler"""
        method = request['method']
        path = request['path']
        route_key = f"{method}:{path}"
        
        # Check for exact route match
        if route_key in self.routes:
            return self.routes[route_key](request)
        
        # Check for static file
        if path.startswith('/static/'):
            return self._serve_static_file(path)
        
        # 404 Not Found
        return self._create_response(404, self._render_404())
        
    def _create_response(self, status_code, body, content_type='text/html', extra_headers=None):
        """Create HTTP response"""
        status_messages = {
            200: 'OK',
            201: 'Created',
            400: 'Bad Request',
            404: 'Not Found',
            405: 'Method Not Allowed',
            500: 'Internal Server Error'
        }
        
        status_message = status_messages.get(status_code, 'Unknown')
        
        headers = {
            'Content-Type': content_type,
            'Content-Length': str(len(body.encode('utf-8'))),
            'Server': 'AryanHTTP/1.0',
            'Date': datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT'),
            'Connection': 'close'
        }
        
        if extra_headers:
            headers.update(extra_headers)
        
        return {
            'status_code': status_code,
            'status_message': status_message,
            'headers': headers,
            'body': body
        }
        
    def _send_response(self, client_socket, response):
        """Send HTTP response to client"""
        # Status line
        response_lines = [
            f"HTTP/1.1 {response['status_code']} {response['status_message']}"
        ]
        
        # Headers
        for key, value in response['headers'].items():
            response_lines.append(f"{key}: {value}")
        
        # Empty line + body
        response_lines.append('')
        response_lines.append(response['body'])
        
        response_str = '\r\n'.join(response_lines)
        client_socket.sendall(response_str.encode('utf-8'))
        
    
    
    def serve_index(self, request):
        """Serve index.html"""
        try:
            with open('index.html', 'r', encoding='utf-8') as f:
                content = f.read()
            return self._create_response(200, content)
        except FileNotFoundError:
            return self._create_response(404, self._render_404())
    
    def serve_book(self, request):
        """Serve book.json"""
        try:
            with open('book.json', 'r', encoding='utf-8') as f:
                content = f.read()
            return self._create_response(200, content, content_type='application/json')
        except FileNotFoundError:
            return self._create_response(404, '{"error": "Book not found"}', 
                                        content_type='application/json')
    
    def serve_stats(self, request):
        """Serve server statistics"""
        stats = {
            'server': 'AryanHTTP/1.0',
            'uptime': 'Dynamic',
            'active_threads': threading.active_count(),
            'timestamp': datetime.utcnow().isoformat()
        }
        return self._create_response(200, json.dumps(stats, indent=2), 
                                    content_type='application/json')
    
    def update_book(self, request):
        """Handle POST request to update book"""
        try:
            body = request['body']
            data = json.loads(body) if body else {}
            
            # Validate and update book.json
            with open('book.json', 'r', encoding='utf-8') as f:
                current_book = json.load(f)
            
            # Merge updates
            current_book.update(data)
            
            with open('book.json', 'w', encoding='utf-8') as f:
                json.dump(current_book, f, indent=2)
            
            return self._create_response(200, json.dumps({
                'success': True,
                'message': 'Book updated successfully',
                'data': current_book
            }), content_type='application/json')
            
        except json.JSONDecodeError:
            return self._create_response(400, '{"error": "Invalid JSON"}', 
                                        content_type='application/json')
        except Exception as e:
            return self._create_response(500, f'{{"error": "{str(e)}"}}', 
                                        content_type='application/json')
    
    def _serve_static_file(self, path):
        """Serve static files"""
        try:
            file_path = path.lstrip('/')
            
            if not os.path.exists(file_path):
                return self._create_response(404, self._render_404())
            
            # Determine content type
            content_type, _ = mimetypes.guess_type(file_path)
            content_type = content_type or 'application/octet-stream'
            
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return self._create_response(200, content, content_type=content_type)
            
        except Exception as e:
            logging.error(f'Error serving static file {path}: {e}')
            return self._create_response(500, 'Internal Server Error')
    
    def _render_404(self):
        """Render 404 error page"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>404 - Not Found</title>
            <style>
                body { font-family: Arial; text-align: center; padding: 50px; background: #0a0e27; color: #e4e4e7; }
                h1 { color: #e74c3c; }
                a { color: #3b82f6; text-decoration: none; }
            </style>
        </head>
        <body>
            <h1>404 - Page Not Found</h1>
            <p>The requested resource was not found on this server.</p>
            <a href="/">Go Home</a>
        </body>
        </html>
        """


def logging_middleware(request):
    """Log all incoming requests"""
    logging.info(f"{request['method']} {request['path']} from {request.get('client_address')}")
    return request

def cors_middleware(request):
    """Add CORS headers"""
    return request


if __name__ == '__main__':
   
    port = int(os.environ.get("PORT", 8080))
    
    server = HTTPServer(host='0.0.0.0', port=port, max_connections=10)
    
    # Add middleware
    server.use(logging_middleware)
    server.use(cors_middleware)
    
    # Start server
    server.start()