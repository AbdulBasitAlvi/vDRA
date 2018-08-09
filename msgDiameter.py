import socket
import binascii
from libDiameter import *

ORIGIN_HOST="dra.telenor.com"
DRA_IP = "10.150.32.2"
ORIGIN_REALM="zte.com"

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
    CEA_avps.append(encodeAVP("Product-Name", "vDRA"))  
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


def hex_to_int(string):
    var = int(string, 16)
    return var

def hex_to_bin(string):
    var = int(string, 16)
    return bin(var)[2:]

def create_CER():   
    # Let's build Capabilites-Exchange Request
    CER_avps=[]  
    CER_avps.append(encodeAVP("Origin-Host", ORIGIN_HOST))  
    CER_avps.append(encodeAVP("Origin-Realm", ORIGIN_REALM))
    CER_avps.append(encodeAVP("Host-IP-Address", DRA_IP))  
    CER_avps.append(encodeAVP("Vendor-Id", 10415))
    CER_avps.append(encodeAVP("Product-Name", "vDRA"))  
    CER_avps.append(encodeAVP('Auth-Application-Id', 16777236))  #3GPP_Gx 
    CER_avps.append(encodeAVP("Vendor-Specific-Application-Id", [
                        encodeAVP("Vendor-Id", 10415), 
                        encodeAVP("Auth-Application-Id", 16777236)]))  #3GPP_Gx  
    # Create message header (empty)  
    CER=HDRItem()  
    # Set command code  
    CER.cmd=257 #Command code of capabilities exchange
    # Set Application-id  
    CER.appId= 0 # Indicates Diameter common messages
    CER.flags = 128
    # Set Hop-by-Hop and End-to-End from request  
    CER.HopByHop=2286269980 #Later replace with a random value
    CER.EndToEnd=8891790 #Late replace with a random value
    # Add AVPs to header and calculate remaining fields  
    ret=createRes(CER,CER_avps)  
    # ret now contains CEA Response as hex string  
    # print ret
    return ret 

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