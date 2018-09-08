import socket
import binascii
from libDiameter import *
from msgDiameter import *
import datetime
import select
import sys
import Queue
import time
import json

#################################### Global Parameters ####################################

user_config = get_user_configurations()
ORIGIN_HOST = str(user_config['dra_parameters']['origin_host'])
DRA_IP  = str(user_config['dra_parameters']['dra_ip'])
ORIGIN_REALM = str(user_config['dra_parameters']['origin_realm'])
DRA_PORT = user_config['dra_parameters']['dra_port']
PCRF_PORT = user_config['pcrf_parameters']['pcrf_port']
PCRF_IP = str(user_config['pcrf_parameters']['pcrf_ip'])
ERROR = -2
SKIP = 2 # Flag used in Skip message for message processing
IS_CCR = 0 # Flag for CCR, If 1 then message is a CCR request
IS_CCA = 1 # Flag for CCA
TIME_INTERVAL = 30
NUM_CCR_REQUESTS = 0
data = {}

#################################### Message Processing ###################################

def process_request(rawdata):
    H=HDRItem()
    stripHdr(H,rawdata)
    dbg="Processing",dictCOMMANDcode2name(H.flags,H.cmd)
    logging.info(dbg)
    if H.cmd==257: # Capabilities-Exchange  
        return create_CEA(rawdata)
    if H.cmd==280: # Device-Watchdog  
        return create_DWA(rawdata)
    if H.cmd==272: # Credit-Control
        variable=splitMsgAVPs(H.msg)
        if H.flags==192:
            DEST_HOST=findAVP("Destination-Host",variable)
            print ("This is a Credit Control Request for Destination Host : " + str(DEST_HOST))
            return IS_CCR
        else:
            #DEST_HOST=findAVP("Destination-Host",variable)
            return IS_CCA
    else:
        return ERROR

###################################### Main Function ######################################

def server_program():

    NUM_CCR_REQUESTS = 0
    START_TIME = time.time()
    END_TIME = time.time() + TIME_INTERVAL

    pcrf_socket = socket.socket()  # Instantiate PCRF connection
    #pcrf_socket.settimeout(10) #Set socket timeout to 5 seconds
    try:
        pcrf_socket.connect((PCRF_IP, PCRF_PORT))  # Connect to PCRF
        print ("Connected to PCRF")
        pcrf_socket.send(create_CER().decode('hex'))  # Send CER to PCRF
        print ("Sent Capabilities-Exchange Request")
        try:
            pcrf_data = pcrf_socket.recv(30000).encode('hex')  # Receive CEA from PCRF
            print("Recieved CEA")
            #DecodeMSG(pcrf_data)
        except socket.error:
            print ("Not connected to PCRF")
    except socket.error:
        print ("Could not connect to PCRF")



    ggsn_socket = socket.socket()
    ggsn_socket.setblocking(0) 
    # ggsn_socket.settimeout(5) #Set socket timeout to 1 second
    ggsn_socket.bind((DRA_IP, DRA_PORT))  # Instantiate GGSN connection
    ggsn_socket.listen(2)  #Configure how many client the server can listen simultaneously
    sockets = [pcrf_socket , ggsn_socket]
    outputs = [ ]
    data = [ ]
    message_queues = {}

    # Give the PCRF connection a queue for data we want to send
    message_queues[pcrf_socket] = Queue.Queue()


    loop_iteration = 1


    while True:      
        print(str(datetime.datetime.now()) + " Loop Iteration = " + str(loop_iteration))

        # Use select to poll through sockets
        read,write,error = select.select(sockets,outputs,[])
        print read
        for rs in read: # Iterate through readable sockets
            print(str(datetime.datetime.now()) + " Readable Socket!")
            if rs is pcrf_socket: # It is PCRF socket
                print(str(datetime.datetime.now()) + " Readable PCRF Socket!")
                pcrf_data = pcrf_socket.recv(30000).encode('hex')
                if not pcrf_data:
                    print(str(datetime.datetime.now()) + ' Disconnected from PCRF')
                    sockets.remove(rs)
                    rs.close()
                else:
                    print (str(datetime.datetime.now()) + " Incomming Data from PCRF")
                    pcrf_return_value = process_request(pcrf_data) #Process Data from PCRF
                    if pcrf_return_value == IS_CCA:
                        print (str(datetime.datetime.now()) +" Sending CCA to GGSN")
                        conn.send(pcrf_data.decode('hex'))
                        print (str(datetime.datetime.now()) +" CCA sent to GGSN") 
                        conn.send(pcrf_data)            
                    else:
                        print (str(datetime.datetime.now()) +" Saving CEA/DWA message to PCRF queue")
                        message_queues[rs].put(pcrf_return_value) #Add message to PCRF Queue
                        if rs not in outputs:   #Add to writable sockets 
                            outputs.append(rs)
                            
            if rs is ggsn_socket:
                conn, address = ggsn_socket.accept()  # Accept new connection on GGSN Socket
                print("Connection to GGSN on IP address: " + str(address))
                print(str(datetime.datetime.now()) + " Readable GGSN Socket!")
                print (str(datetime.datetime.now()) + " Fetching Data from GGSN")
                sockets.append(conn)
            else: 
                ggsn_data = conn.recv(30000).encode('hex') # GGSN has data to send!
                if not ggsn_data:
                    print(str(datetime.datetime.now()) + ' Disconnected from GGSN')
                    sockets.remove(rs)
                    rs.close()
                else:
                    ggsn_return_value = process_request(ggsn_data)  
                    if ggsn_return_value == ERROR:
                        print (str(datetime.datetime.now()) + " Error decoding Diameter message")
                    if ggsn_return_value == IS_CCR:
                        print (str(datetime.datetime.now()) +" Saving CCR message to PCRF queue")
                        NUM_CCR_REQUESTS = NUM_CCR_REQUESTS + 1
                        message_queues[pcrf_socket].put(ggsn_data) #Add message to PCRF Queue
                        if rs not in outputs:   #Add to writable sockets 
                            outputs.append(rs)
                    else:
                        if ggsn_return_value == SKIP:
                            print (str(datetime.datetime.now()) + " This is an Answer message")
                        else:
                            print (str(datetime.datetime.now()) + " Sending CEA/DWA to GGSN")
                            conn.send(ggsn_return_value.upper().decode('hex')) #Send CEA and DWA to GGSN


        for s in write:
            print(str(datetime.datetime.now()) + "Writable PCRF Socket!")
            try:
                next_msg = message_queues[s].get_nowait()
            except Queue.Empty:
                # No messages waiting so stop checking for writability.
                print (str(datetime.datetime.now()) + " PCRF Queue is Empty!")
                outputs.remove(s)
            except KeyError:
                print (str(datetime.datetime.now()) + " KeyError!")
            else:
                s.send(next_msg.upper().decode('hex')) #Send CEA and DWA to PCRF
                print (str(datetime.datetime.now()) + " Message sent to PCRF")


        if END_TIME <= time.time():
            print (str(datetime.datetime.now()) + " Writing data to file")
            data.append([current_milli_time(), NUM_CCR_REQUESTS])
            with open('/var/www/html/data.json', 'w') as filehandle:  
                json.dump(data, filehandle)
            NUM_CCR_REQUESTS = 0
            END_TIME = time.time() + TIME_INTERVAL

        loop_iteration = loop_iteration + 1


if __name__ == '__main__':
    LoadDictionary("/root/dictDiameter.xml")
    server_program()
