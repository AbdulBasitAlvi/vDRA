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
IS_RAR = 5
IS_RAA = 6
TIME_INTERVAL = 300
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
    if H.cmd==258: # Credit-Control
        variable=splitMsgAVPs(H.msg)
        if H.flags==192:
            DEST_HOST=findAVP("Destination-Host",variable)
            print ("This is a Re-Auth Request for Destination Host : " + str(DEST_HOST))
            return IS_RAR
        else:
            #DEST_HOST=findAVP("Destination-Host",variable)
            return IS_RAA
    else:
        return ERROR

##################################### PCRF Connection ####################################

def connect_pcrf():
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
        return pcrf_socket
    except socket.error:
        print ("Could not connect to PCRF")

###################################### Main Function ######################################

def server_program():

    NUM_CCR_REQUESTS = 0
    START_TIME = time.time()
    END_TIME = time.time() + TIME_INTERVAL

    #Connect to PCRF
    pcrf_socket = connect_pcrf()

    #Instantiate GGSN socket for vDRA
    ggsn_socket = socket.socket()
    ggsn_socket.setblocking(0) 
    #ggsn_socket.settimeout(5) #Set socket timeout to 1 second
    ggsn_socket.bind((DRA_IP, DRA_PORT))  # Instantiate GGSN connection
    ggsn_socket.listen(5)  #Configure how many client the server can listen simultaneously

    #Instantiate Parameters for select funtion
    sockets = [pcrf_socket , ggsn_socket]
    outputs = [ ]
    data = [ ]
    message_queues = {}
    loop_iteration = 1

    # Give the PCRF connection a queue for data we want to send
    message_queues[pcrf_socket] = Queue.Queue(maxsize=0)

    # Start While Loop for DRA Engine
    while True:      
        print(str(datetime.datetime.now()) + " Loop Iteration = " + str(loop_iteration))

        # Use select to poll through sockets
        try:
            read,write,exceptional = select.select(sockets,outputs,sockets)
        except:
            print(str(datetime.datetime.now()) + " Could not Poll Sockets!")
            continue #Use continue to try to poll again


        print read
        for rs in read: # Iterate through readable sockets
            print(str(datetime.datetime.now()) + " Readable Socket!")

            #Readable socket means either data to recieve from PCRF, Data to recieve from GGSN or new connection to vDRA

            #New GGSN wants to establish connection to vDRA
            if rs is ggsn_socket:
                conn, address = ggsn_socket.accept()  #Accept new connection on GGSN Socket to vDRA
                print("Connection to GGSN on IP address: " + str(address))
                print(str(datetime.datetime.now()) + " Readable GGSN Socket!")
                print (str(datetime.datetime.now()) + " Fetching Data from GGSN")
                sockets.append(conn)

                #Handle CEA and CER for minimum delay

                ggsn_data = conn.recv(30000).encode('hex') # GGSN is sending CER
                ggsn_return_value = process_request(ggsn_data) # Process Request
                print (str(datetime.datetime.now()) + " Sending CEA to GGSN")
                try:
                    conn.send(ggsn_return_value.upper().decode('hex')) #Send CEA to GGSN
                except:
                    print (str(datetime.datetime.now()) + " Could not send CEA to GGSN")

            #Readable PCRF socket, so PCRF has data to send

            if rs is pcrf_socket:             
                print(str(datetime.datetime.now()) + " Readable PCRF Socket!")
                try:
                    pcrf_data = pcrf_socket.recv(30000).encode('hex')
                    if not pcrf_data: #A readable socket with No Data means the connection has been closed from PCRF End
                        print(str(datetime.datetime.now()) + ' Disconnected from PCRF')
                        sockets.remove(rs)
                        print(str(datetime.datetime.now()) + ' Closing Socket from PCRF')
                        rs.close()
                        print(str(datetime.datetime.now()) + ' Deleting PCRF Queue')
                        del message_queues[pcrf_socket]

                        #Re-Connect to PCRF
                        pcrf_socket = connect_pcrf()
                        sockets.append(pcrf_socket)
                        message_queues[pcrf_socket] = Queue.Queue(maxsize=0)

                    else:
                        print (str(datetime.datetime.now()) + " Incomming Data from PCRF")
                        pcrf_return_value = process_request(pcrf_data) #Process Data from PCRF
                        if pcrf_return_value == ERROR:
                            print (str(datetime.datetime.now()) + " Error decoding Diameter message PCRF")
                        elif pcrf_return_value == IS_CCA:
                            print (str(datetime.datetime.now()) +" Sending CCA to GGSN")
                            conn.send(pcrf_data.decode('hex'))
                            print (str(datetime.datetime.now()) +" CCA sent to GGSN") 
                            conn.send(pcrf_data)
                        else:
                            print (str(datetime.datetime.now()) +" Saving CEA/DWA message to PCRF queue")
                            message_queues[pcrf_socket].put(pcrf_return_value) #Add message to PCRF Queue
                            if rs not in outputs:   #Add to writable sockets 
                                outputs.append(pcrf_socket)

                except:
                    print(str(datetime.datetime.now()) + ' PCRF Hanged Up!!')

                        
            #Readable GGSN socket, so GGSN has data to send
            else: 
                ggsn_data = conn.recv(30000).encode('hex') # GGSN has data to send!
                if not ggsn_data:
                    print(str(datetime.datetime.now()) + ' Disconnected from GGSN')
                    sockets.remove(rs)
                    rs.close()
                    continue
                else:
                    ggsn_return_value = process_request(ggsn_data)  
                    if ggsn_return_value == ERROR:
                        print (str(datetime.datetime.now()) + " Error decoding Diameter message GGSN")
                    elif ggsn_return_value == IS_CCR:
                        print (str(datetime.datetime.now()) +" Saving CCR message to PCRF queue")
                        NUM_CCR_REQUESTS = NUM_CCR_REQUESTS + 1
                        message_queues[pcrf_socket].put(ggsn_data) #Add message to PCRF Queue
                        if rs not in outputs:   #Add to writable sockets 
                            outputs.append(pcrf_socket)
                    else:
                        if ggsn_return_value == SKIP:
                            print (str(datetime.datetime.now()) + " This is an Answer message")
                        else:
                            print (str(datetime.datetime.now()) + " Sending CEA/DWA to GGSN")
                            conn.send(ggsn_return_value.upper().decode('hex')) #Send CEA and DWA to GGSN


        for s in write:
            #Writable PCRF socket!
            if s is pcrf_socket:
                print(str(datetime.datetime.now()) + "Writable PCRF Socket!")
                try:
                    next_msg = message_queues[pcrf_socket].get_nowait()
                except Queue.Empty:
                    # No messages waiting so stop checking for writability.
                    print (str(datetime.datetime.now()) + " PCRF Queue is Empty!")
                    try:
                        outputs.remove(s)
                    except:
                        print (str(datetime.datetime.now()) + " Not in List!!")
                except KeyError:
                    print (str(datetime.datetime.now()) + " There is a Key Error on PCRF Socket!")
                    outputs.remove(s)
                else:
                    try:
                        pcrf_socket.send(next_msg.upper().decode('hex')) #Send Message to PCRF
                        print (str(datetime.datetime.now()) + " Message sent to PCRF")
                    except:
                        print (str(datetime.datetime.now()) + " Unknown Message")
                        print (next_msg)
            else:
                print(str(datetime.datetime.now()) + "Unknown Write!")


        for s in exceptional:
            print(str(datetime.datetime.now()) + "Exceptional Socket Found! Socket in Error State")
            # Stop listening for input on the connection
            sockets.remove(s)
            if s in outputs:
                outputs.remove(s)
            s.close()

            # Remove message queue
            #del message_queues[s]


        #This condition is for counters
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
