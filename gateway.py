import socket
import time

def client_program():
        host = 'dra.zte.com'  # as both code is running on same pc
        port = 5001  # socket server port number

        client_socket = socket.socket()  # instantiate
        client_socket.connect((host, port))  # connect to the server


#    message = input(" -> ")  # take input
        CCR_message = "010000d08000010100000000069be694413864d5000001084000002f70637363662e696d732e6d6e633030362e6d63633431302e336770706e6574776f726b2e6f7267000000012840000029696d732e6d6e633030362e6d63633431302e336770706e6574776f726b2e6f7267000000000001014000000e00010a96501200000000010a4000000c000028af0000010d00000015434469616d657465725065657200000000000104400000200000010a4000000c000028af000001024000000c01000014000001024000000c01000014"
        CCR_message = CCR_message.upper().decode('hex')
#       print CCR_message
        client_socket.send(CCR_message)  # send message
        data = client_socket.recv(10000).encode('ex')  # receive response

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