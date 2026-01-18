import socket

SERVER_HOST = '0.0.0.0'
SERVER_PORT = 8080
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((SERVER_HOST, SERVER_PORT))
server_socket.listen(5)

print(f'Listening on port {SERVER_PORT} ...')

while True: 
    try:
        client_socket, client_address = server_socket.accept()
        print(f'Connection from {client_address}')
        
        request = client_socket.recv(1500).decode()
        print(request)

        # Parse HTTP request
        lines = request.split('\n')
        if len(lines) == 0:
            continue
            
        first_line = lines[0].split()
        if len(first_line) < 2:
            continue
            
        http_method = first_line[0]
        path = first_line[1]

        # Route handling
        if http_method == 'GET':
            if path == '/':
                try:
                    with open('index.html', 'r') as fin:
                        content = fin.read()
                    response = 'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n' + content
                except FileNotFoundError:
                    response = 'HTTP/1.1 404 Not Found\r\n\r\n<h1>404 - index.html not found</h1>'
                    
            elif path == '/book':
                try:
                    with open('book.json', 'r') as fin:
                        content = fin.read()
                    response = 'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n' + content
                except FileNotFoundError:
                    response = 'HTTP/1.1 404 Not Found\r\n\r\n{"error": "book.json not found"}'
                    
            else:
                # Handle 404 for unknown paths
                response = 'HTTP/1.1 404 Not Found\r\n\r\n<h1>404 - Page Not Found</h1>'
        else:
            # Handle non-GET methods
            response = 'HTTP/1.1 405 Method Not Allowed\r\n\r\nAllow: GET'

        client_socket.sendall(response.encode())
        client_socket.close()
        
    except Exception as e:
        print(f'Error: {e}')
        try:
            client_socket.close()
        except:
            pass

server_socket.close()