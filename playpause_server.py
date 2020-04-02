import socket
import select
import string
import random
import time

HEADER_LENGTH = 10

PORT = 65080

# Create a socket
# socket.AF_INET - address family, IPv4, some other possible are AF_INET6, AF_BLUETOOTH, AF_UNIX
# socket.SOCK_STREAM - TCP, conection-based, socket.SOCK_DGRAM - UDP, connectionless, datagrams, socket.SOCK_RAW - raw IP packets
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# SO_ - socket option
# SOL_ - socket option level
# Sets REUSEADDR (as a socket option) to 1 on socket
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# Bind, so server informs operating system that it's going to use given IP and port
# For a server using 0.0.0.0 means to listen on all available interfaces, useful to connect locally to 127.0.0.1 and remotely to LAN interface IP
IP = socket.gethostname()
server_socket.bind((IP, PORT))

# This makes server listen to new connections
server_socket.listen()

# List of sockets for select.select()
sockets_list = [server_socket]

# List of connected clients - socket as a key, user header and name as data
clients = {}
session_pools = {}

print(f'Listening for connections on {IP}:{PORT}...')

# Handles message receiving
def receive_message(client_socket):

    try:

        # Receive our "header" containing message length, it's size is defined and constant
        message_header = client_socket.recv(HEADER_LENGTH)

        # If we received no data, client gracefully closed a connection, for example using socket.close() or socket.shutdown(socket.SHUT_RDWR)
        if not len(message_header):
            return False

        # Convert header to int value
        message_length = int(message_header.decode('utf-8').strip())

        # Return an object of message header and message data
        return {'header': message_header, 'data': client_socket.recv(message_length)}

    except:

        # If we are here, client closed connection violently, for example by pressing ctrl+c on his script
        # or just lost his connection
        # socket.close() also invokes socket.shutdown(socket.SHUT_RDWR) what sends information about closing the socket (shutdown read/write)
        # and that's also a cause when we receive an empty message
        return False

def generate_session_id():
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(6))

def end_socket(socket):
    # Remove from list for socket.socket()
    sockets_list.remove(notified_socket)
    parsed_user_data = clients[notified_socket]
    session_pools[parsed_user_data["session_id"]].remove(notified_socket)
    # Remove from our list of users
    del clients[notified_socket]

def user_info_parser(user_info):
    user_data = user_info['data'].decode('utf-8').split(":")
    new_user_header = f"{len(user_data[0]):<{HEADER_LENGTH}}".encode('utf-8')
    return {'header': new_user_header, 'name': user_data[0].encode("utf-8"), 'session_id': user_data[1]}

while True:

    # Calls Unix select() system call or Windows select() WinSock call with three parameters:
    #   - rlist - sockets to be monitored for incoming data
    #   - wlist - sockets for data to be send to (checks if for example buffers are not full and socket is ready to send some data)
    #   - xlist - sockets to be monitored for exceptions (we want to monitor all sockets for errors, so we can use rlist)
    # Returns lists:
    #   - reading - sockets we received some data on (that way we don't have to check sockets manually)
    #   - writing - sockets ready for data to be send thru them
    #   - errors  - sockets with some exceptions
    # This is a blocking call, code execution will "wait" here and "get" notified in case any action should be taken
    read_sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list)


    # Iterate over notified sockets
    for notified_socket in read_sockets:

        # If notified socket is a server socket - new connection, accept it
        if notified_socket == server_socket:

            # Accept new connection
            # That gives us new socket - client socket, connected to this given client only, it's unique for that client
            # The other returned object is ip/port set
            client_socket, client_address = server_socket.accept()

            # Client should send their name and session id right away, receive it
            user_info = receive_message(client_socket)

            # If False - client disconnected before sending info
            if user_info is False:
                continue

            parsed_user_data = user_info_parser(user_info)

            user_name = parsed_user_data["name"]
            session_id = parsed_user_data["session_id"]

            # Add accepted socket to select.select() list
            sockets_list.append(client_socket)

            # Session Creator
            if session_id == '':
                session_id = generate_session_id()
                parsed_user_data["session_id"] = session_id

            # Session pool doesn't exist
            if session_id not in session_pools:
                session_pools[session_id] = []
            print(client_socket)
            session_pools[session_id].append(client_socket)

            # Also save username and username header
            clients[client_socket] = parsed_user_data

            print('Accepted new connection from {}:{}, username: {}'.format(*client_address, user_name.decode('utf-8')))
            message = f"Thanks for connecting, your session id is: {session_id}"
            message_header = f"{len(message):<{HEADER_LENGTH}}"
            server_name = "Server"
            server_header = f"{len(server_name):<{HEADER_LENGTH}}"
            time.sleep(0.5)
            client_socket.send(server_header.encode('utf-8') + server_name.encode('utf-8') + message_header.encode('utf-8') + message.encode('utf-8'))

        # Else existing socket is sending a message
        else:
            # Receive message
            message = receive_message(notified_socket)

            # If False, client disconnected, cleanup
            if message is False:
                print('Closed connection from: {}'.format(clients[notified_socket]['name'].decode('utf-8')))
                end_socket(notified_socket)
                continue

            # Get user by notified socket, so we will know who sent the message
            user = clients[notified_socket]

            # Iterate over connected clients and broadcast message
            for pool_socket in session_pools[user["session_id"]]:
                # But don't sent it to sender
                if pool_socket != notified_socket:
                    # Send user and message (both with their headers)
                    # We are reusing here message header sent by sender, and saved username header send by user when he connected
                    pool_socket.send(user['header'] + user['name'] + message['header'] + message['data'])

    # It's not really necessary to have this, but will handle some socket exceptions just in case
    for notified_socket in exception_sockets:
        end_socket(notified_socket)