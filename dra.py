import socket
import binascii
from libDiameter import *
from msgDiameter import *

PCRF_PORT = 5001
PCRF_IP = "10.248.125.144"
DRA_PORT = 6000
DRA_IP = "10.150.32.2"
SKIP = 2 # Flag used in Skip message for message processing
IS_CCR = 0 # Flag for CCR, If 1 then message is a CCR request
IS_CCA = 1 # Flag for CCA
ORIGIN_HOST="dra.zte.com"
ORIGIN_REALM="zte.com"
VENDOR_ID = 10415


def process_request(rawdata):
    H=HDRItem()
    stripHdr(H,rawdata)
    dbg="Processing",dictCOMMANDcode2name(H.flags,H.cmd)
    logging.info(dbg)
    if H.flags & DIAMETER_HDR_REQUEST==0:
        # If Answer no need to do anything  
        return SKIP
    if H.cmd==257: # Capabilities-Exchange  
        return create_CEA(rawdata)
    if H.cmd==280: # Device-Watchdog  
        return create_DWA(rawdata)
    if H.cmd==272: # Credit-Control
        variable=splitMsgAVPs(H.msg)
        if H.flags==192:
            DEST_HOST=findAVP("Destination-Host",variable)
            print ("This is a Credit Control Request for Destination Host : " + DEST_HOST)
            return IS_CCR
        else:
            DEST_HOST=findAVP("Destination-Host",variable)
            print ("This is a Credit Control Answer for Destination Host : " + DEST_HOST)
            return IS_CCA

    return create_UTC(rawdata,"Unknown command code")         


def server_program():

    pcrf_socket = socket.socket()  # Instantiate PCRF connection
    try:
        pcrf_socket.connect((PCRF_IP, PCRF_PORT))  # Connect to PCRF
        print ("Connected to PCRF")
        pcrf_socket.send(create_CER().decode('hex'))  # Send CER to PCRF
        print ("Sent Capabilities-Exchange Request")
        print("Recieved CER")
        try:
            pcrf_data = pcrf_socket.recv(10000).encode('hex')  # Receive CEA from PCRF
            DecodeMSG(pcrf_data)
        except socket.error:
            print ("Not connected to PCRF")
    except socket.error:
        print ("Could not connect to PCRF")


    ggsn_socket = socket.socket() 
    ggsn_socket.bind((DRA_IP, DRA_PORT))  # Instantiate GGSN connection
    ggsn_socket.listen(2)  #Configure how many client the server can listen simultaneously
    conn, address = ggsn_socket.accept()  # Accept new connection

    print("Connection from: " + str(address))

    while True:
        # Recieve data from PCRF
        pcrf_data = pcrf_socket.recv(10000).encode('hex')
        if not pcrf_data:
        # If data is not recieved from PCRF
            print ("No data to recieve from PCRF")
        else:
            pcrf_return_value = process_request(pcrf_data)
            print ("Incomming Data from PCRF")
            DecodeMSG(pcrf_data)       
            if pcrf_return_value == ERROR:
                print ("Error decoding Diameter message")
            if pcrf_return_value == IS_CCR:
                conn.send(pcrf_data.decode('hex')) # Send CCA to GGSN
            else:
                if pcrf_return_value == SKIP:
                    print ("This is an Answer message")
                else:
                    print ("Sending reply to PCRF")
                    print (DecodeMSG(pcrf_return_value.upper()))
                    pcrf_socket.send(pcrf_return_value.upper().decode('hex')) #Send CEA and DWA to PCRF


        # Recieve data from GGSN
        ggsn_data = conn.recv(10000).encode('hex') 
        if not ggsn_data:
        # If data is not received from GGSN skip the loop
            continue

        #Decode diameter Header from GGSN
        diameter_header(ggsn_data)
        DecodeMSG(ggsn_data)

        # Process incomming data from GGSN
        ggsn_return_value = process_request(ggsn_data)        
        if ggsn_return_value == ERROR:
            print ("Error decoding Diameter message")
        if ggsn_return_value == IS_CCR:
            pcrf_socket.send(ggsn_data.decode('hex')) # Send CCR to PCRF
        else:
            if ggsn_return_value == SKIP:
                print ("This is an Answer message")
            else:
                conn.send(ggsn_return_value.upper().decode('hex')) #Send CEA and DWA to GGSN

    conn.close()  # close the connection
    pcrf_socket.close()


if __name__ == '__main__':
    LoadDictionary("/root/dictDiameter.xml")
    server_program()
