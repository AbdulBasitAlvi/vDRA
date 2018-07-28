import socket
import binascii
from libDiameter import *

def DecodeMSG(msg):
    H=HDRItem()
    stripHdr(H,msg)
    avps=splitMsgAVPs(H.msg)
    cmd=dictCOMMANDcode2name(H.flags,H.cmd)
    if cmd==ERROR:
        print 'Unknown command',H.cmd
    else:
        print cmd
    print "Hop-by-Hop=",H.HopByHop,"End-to-End=",H.EndToEnd,"ApplicationId=",H.appId
    for avp in avps:
      print "RAW AVP",avp
      print "Decoded AVP",decodeAVP(avp)
    print "-"*30

def create_CEA(msg):  
    H=HDRItem()
    stripHdr(H,msg)
    global DEST_REALM  
    CER_avps=splitMsgAVPs(H.msg)  
    DEST_REALM=findAVP("Origin-Realm",CER_avps)    
    # Let's build Capabilites-Exchange Answer  
    CEA_avps=[]  
    CEA_avps.append(encodeAVP("Origin-Host", ORIGIN_HOST))  
    CEA_avps.append(encodeAVP("Origin-Realm", ORIGIN_REALM))  
    CEA_avps.append(encodeAVP("Product-Name", "OCS-SIM"))  
    CEA_avps.append(encodeAVP('Auth-Application-Id', 4))  
    CEA_avps.append(encodeAVP("Supported-Vendor-Id", 10415))  
    CEA_avps.append(encodeAVP("Result-Code", 2001))  #DIAMETER_SUCCESS 2001  
    # Create message header (empty)  
    CEA=HDRItem()  
    # Set command code  
    CEA.cmd=H.cmd  
    # Set Application-id  
    CEA.appId=H.appId  
    # Set Hop-by-Hop and End-to-End from request  
    CEA.HopByHop=H.HopByHop  
    CEA.EndToEnd=H.EndToEnd  
    # Add AVPs to header and calculate remaining fields  
    ret=createRes(CEA,CEA_avps)  
    # ret now contains CEA Response as hex string  
    print ret
    return ret 

def create_DWA(msg):
    H=HDRItem()
    stripHdr(H,msg)
    # Let's build Diameter-WatchdogAnswer   
    DWA_avps=[]
    DWA_avps.append(encodeAVP("Origin-Host", ORIGIN_HOST))
    DWA_avps.append(encodeAVP("Origin-Realm", ORIGIN_REALM))
    DWA_avps.append(encodeAVP("Result-Code", 2001)) #DIAMETER_SUCCESS 2001  
    # Create message header (empty)  
    DWA=HDRItem()
    # Set command code  
    DWA.cmd=H.cmd
    # Set Application-id  
    DWA.appId=H.appId
    # Set Hop-by-Hop and End-to-End from request  
    DWA.HopByHop=H.HopByHop
    DWA.EndToEnd=H.EndToEnd
    # Add AVPs to header and calculate remaining fields  
    ret=createRes(DWA,DWA_avps)
    # ret now contains DWA Response as hex string  
    return ret
    # Create Disconnect_Peer response in reply to Disconnect_Peer request. We just reply with 2001 OK for testing purposes           


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
        DEST_HOST=findAVP("Destination-Host",variable)
        print ("This is a CCR message for destination host :"+ str(DEST_HOST))
        return SKIP
    return create_UTC(rawdata,"Unknown command code")         


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
        DEST_HOST=findAVP("Destination-Host",variable)
        print ("This is a CCR message for destination host :"+ str(DEST_HOST))
        return SKIP
    return create_UTC(rawdata,"Unknown command code")


def hex_to_int(string):
    var = int(string, 16)
    return var

def hex_to_bin(string):
    var = int(string, 16)
    return bin(var)[2:]

def diameter_header(raw_data):
    string = str(raw_data)
#    print string
    version = hex_to_int(string[0:2])
    length = hex_to_int(string[2:8])
    flags = hex_to_bin(string[8:10])
    command_code = hex_to_int(string[10:16])
    application_id = hex_to_int(string[16:24])
    hop_id = hex_to_int(string[24:32])
    end_id = hex_to_int(string[32:40])

    print ("Version : " +str(version))
    print ("Length :  " +str(length))
    print ("Flags : " + str(flags))
    print ("Command Code : " + str(command_code))
    print ("Application ID : " + str(application_id))
    print ("Hop-by-Hop Identifier: " + str(hop_id))
    print ("End-to-End Identifier: " + str(end_id))


def server_program():
    # get the hostname
    host = socket.gethostname()
    port = 5001  # initiate port no above 1024

    server_socket = socket.socket()  # get instance
    # look closely. The bind() function takes tuple as argument
    server_socket.bind((host, port))  # bind host address and port together

    # configure how many client the server can listen simultaneously
    server_socket.listen(2)
    conn, address = server_socket.accept()  # accept new connection

    print("Connection from: " + str(address))

    while True:
        # receive data stream. it won't accept data packet greater than 1024 bytes
        data = conn.recv(10000).encode('hex') # See encoding scheme and match here

        #If encoding is not in HEX insert function here to convert data into hex

        if not data:
         # if data is not received break
                continue

        print data

        diameter_header(data)
        return_value = process_request(data)
        DecodeMSG(data)
        if return_value == ERROR:
            print ("Error decoding Diameter message")
        else:
            if return_value == SKIP:
                print ("Saving and storing data to send to Host")
            else:
                conn.send(return_value.upper().decode('hex'))


#        data = raw_input(' -> ')
#        conn.send(data.encode())  # send data to the client

    conn.close()  # close the connection


if __name__ == '__main__':
    SKIP = 0
    ORIGIN_HOST="dra.zte.com"
    IP_ADDRESS="192.168.1.40"
    ORIGIN_REALM="zte.com"
    LoadDictionary("/root/dictDiameter.xml")
    server_program()