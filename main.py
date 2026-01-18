import os
import socket
import json
import threading
from datetime import datetime

SERVER_HOST = '0.0.0.0'
SERVER_PORT = int(os.environ.get("PORT", 8080)) 

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((SERVER_HOST, SERVER_PORT))
server_socket.listen(5)

print(f'Listening on port {SERVER_PORT} ...')

while True: 
    try:
        client_socket, client_address = server_socket.accept()
        print(f'Connection from {client_address}')
        
        request = client_socket.recv(4096).decode('utf-8')
        print(request)

        # Parse HTTP request
        lines = request.split('\n')
        if len(lines) == 0:
            client_socket.close()
            continue
            
        first_line = lines[0].split()
        if len(first_line) < 2:
            client_socket.close()
            continue
            
        http_method = first_line[0]
        path = first_line[1]
        
        # Parse request body for POST requests
        body = ''
        if http_method == 'POST':
            try:
                # Find the body after the blank line
                body_start = request.find('\r\n\r\n')
                if body_start != -1:
                    body = request[body_start + 4:]
            except:
                pass

        # Route handling
        if http_method == 'GET':
            if path == '/':
                try:
                    with open('index.html', 'r', encoding='utf-8') as fin:
                        content = fin.read()
                    
                    response = 'HTTP/1.1 200 OK\r\n'
                    response += 'Content-Type: text/html; charset=utf-8\r\n'
                    response += f'Content-Length: {len(content.encode("utf-8"))}\r\n'
                    response += 'Connection: close\r\n'
                    response += '\r\n'
                    response += content
                    
                except FileNotFoundError:
                    response = 'HTTP/1.1 404 Not Found\r\n\r\n<h1>404 - index.html not found</h1>'
                    
            elif path == '/book':
                try:
                    with open('book.json', 'r', encoding='utf-8') as fin:
                        content = fin.read()
                  
                    response = 'HTTP/1.1 200 OK\r\n'
                    response += 'Content-Type: application/json\r\n'
                    response += 'Access-Control-Allow-Origin: *\r\n'
                    response += f'Content-Length: {len(content.encode("utf-8"))}\r\n'
                    response += 'Connection: close\r\n'
                    response += '\r\n'
                    response += content

                except FileNotFoundError:
                    response = 'HTTP/1.1 404 Not Found\r\n\r\n{"error": "book.json not found"}'
            
            elif path == '/api/stats':
                stats = {
                    'server': 'AryanHTTP/1.0',
                    'active_threads': threading.active_count(),
                    'timestamp': datetime.utcnow().isoformat()
                }
                content = json.dumps(stats, indent=2)
                
                response = 'HTTP/1.1 200 OK\r\n'
                response += 'Content-Type: application/json\r\n'
                response += 'Access-Control-Allow-Origin: *\r\n'
                response += f'Content-Length: {len(content.encode("utf-8"))}\r\n'
                response += 'Connection: close\r\n'
                response += '\r\n'
                response += content
                    
            else:
                # Handle 404 for unknown paths
                response = 'HTTP/1.1 404 Not Found\r\n'
                response += 'Content-Type: text/html; charset=utf-8\r\n'
                response += 'Connection: close\r\n'
                response += '\r\n'
                response += '<h1>404 - Page Not Found</h1>'
                
        elif http_method == 'POST':
            if path == '/api/book':
                try:
                    # Parse POST body
                    data = json.loads(body) if body else {}
                    
                    # Read current book data
                    with open('book.json', 'r', encoding='utf-8') as f:
                        current_book = json.load(f)
                    
                    # Update book data
                    current_book.update(data)
                    
                    # Write updated data back
                    with open('book.json', 'w', encoding='utf-8') as f:
                        json.dump(current_book, f, indent=2)
                    
                    # Send success response
                    result = {
                        'success': True,
                        'message': 'Book updated successfully',
                        'data': current_book
                    }
                    content = json.dumps(result, indent=2)
                    
                    response = 'HTTP/1.1 200 OK\r\n'
                    response += 'Content-Type: application/json\r\n'
                    response += 'Access-Control-Allow-Origin: *\r\n'
                    response += f'Content-Length: {len(content.encode("utf-8"))}\r\n'
                    response += 'Connection: close\r\n'
                    response += '\r\n'
                    response += content
                    
                except json.JSONDecodeError:
                    error = '{"error": "Invalid JSON"}'
                    response = 'HTTP/1.1 400 Bad Request\r\n'
                    response += 'Content-Type: application/json\r\n'
                    response += f'Content-Length: {len(error)}\r\n'
                    response += 'Connection: close\r\n'
                    response += '\r\n'
                    response += error
                    
                except Exception as e:
                    error = json.dumps({'error': str(e)})
                    response = 'HTTP/1.1 500 Internal Server Error\r\n'
                    response += 'Content-Type: application/json\r\n'
                    response += f'Content-Length: {len(error)}\r\n'
                    response += 'Connection: close\r\n'
                    response += '\r\n'
                    response += error
            else:
                # Handle 404 for unknown POST paths
                response = 'HTTP/1.1 404 Not Found\r\n'
                response += 'Content-Type: application/json\r\n'
                response += 'Connection: close\r\n'
                response += '\r\n'
                response += '{"error": "Endpoint not found"}'
                
        else:
            # Handle non-GET/POST methods
            response = 'HTTP/1.1 405 Method Not Allowed\r\n'
            response += 'Allow: GET, POST\r\n'
            response += 'Connection: close\r\n'
            response += '\r\n'

        client_socket.sendall(response.encode('utf-8'))
        client_socket.close()
        
    except Exception as e:
        print(f'Error: {e}')
        try:
            client_socket.close()
        except:
            pass

server_socket.close()