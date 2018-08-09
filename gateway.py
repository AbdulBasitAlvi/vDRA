import socket
import time

def client_program():
        host = 'dra.zte.com'  # as both code is running on same pc
        port = 6000  # socket server port number

        client_socket = socket.socket()  # instantiate
        client_socket.connect((host, port))  # connect to the server


#    message = input(" -> ")  # take input
        CCR_message = "0100008C80000101000000008845B61C0087AD8E00000108400000136472612e7a74652e636f6d00000001284000000F7a74652e636f6d00000001014000000E00010a96200200000000010A4000000C000028af0000010D0000000C76445241000001024000000C0100001400000104400000200000010a4000000c000028af000001024000000c01000014"
        CCR_message = CCR_message.upper().decode('hex')
#       print CCR_message
        client_socket.send(CCR_message)  # send message
        data = client_socket.recv(10000).encode('hex')  # receive response

        print('Received from server: ' + data)  # show in terminal

        while True:
                CCR_message = "010000448000011800000000E712FFFF0120483D0000010840000014706372662E7A74652E636F6D000001284000000F7A74652E636F6D00000001164000000C00000000"
                CCR_message = CCR_message.upper().decode('hex')
        #       print CCR_message
                client_socket.send(CCR_message)  # send message
                data = client_socket.recv(10000).encode('hex')  # receive response

                print('Received from server: ' + data)  # show in terminal 
                time.sleep(30)


#    data = client_socket.recv(1024).decode()  # receive response

#    print('Received from server: ' + data)  # show in terminal

#    message = raw_input(" -> ")  # again take input

        client_socket.close()  # close the connection


if __name__ == '__main__':
        client_program()