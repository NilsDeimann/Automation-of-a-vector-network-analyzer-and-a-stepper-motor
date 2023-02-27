from ctypes import *
import time
import os
import sys
import platform
import tempfile
import re
import socket
import struct
#import matplotlib.pyplot as plt
#from pylab import *

# =========================== Connecting to VNA ===============================

try:
	#create an AF_INET, STREAM socket (TCP)
	instrumentDirectSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
except socket.error as msg:
    print('Failed to create socket. Error code: ' + str(msg[0]) + ' , Error message : ' + msg[1])
    instrumentDirectSocket.exit();

print('Socket Created')

# Alter this host name, or IP address, in the line below to accommodate your specific instrument
host = '134.61.12.182' # Or you could utilize an IP address.

# Alter the socket port number in the line below to accommodate your 
# specific instrument socket port. Traditionally, most Keysight Technologies, 
# Agilent Technologies, LAN based RF instrumentation socket ports use 5025. 
# Refer to your specific instrument User Guide for additional details.
port = 5025
#
# A delay time variable for the sleep function call, unit is seconds
# For clarification of the use of the waitTime variable used in the sleep timer call
# please refer to any one of these function calls and the notes on the timer use:
    # getDataAsAsciiTransfer() - FUNCTION
    # getDataAsBinBlockTransfer() - FUNCTION 
    # getStimulusArrayAsBinBlock() - FUNCTION
waitTime = 0.2
#

# The measureSelectFormat variable may be used in future releases.
# The following notes are an exceprt from the determineDataArraySize(): function call
# and are repeated below for clarity
   # Those formats returning one dimensional arrays are 
   # MLINear,MLOGarithmic,PHASe,UPHase 'Unwrapped phase,
   # IMAGinary,REAL,SWR,GDELay 'Group Delay,KELVin,FAHRenheit,CELSius. 
   # Those FORMats returning    # 2x number of points data arrays (for FDATA query) are POLar,'
   # SMITh,'SADMittance 'Smith Admittance
# Start by setting the measSelectFormat variable to "" null. 
measSelectFormat = ""

# Variables for the center frequency, frequency span, 
# IF Bandwidth and Number of Trace Points.
centerFrequency =  19E9
frequencySpan = 3E9
ifBandWidth = 50000
sweepPoints = 16384
powerLevel = -20
calName = '"{30ABF31F-FE85-4A9D-A5E6-2432937BD2C1}"'

try:
	remote_ip = socket.gethostbyname( host )
except socket.gaierror:
	#could not resolve
	print('Hostname could not be resolved. Exiting')
	instrumentDirectSocket.exit()
	
print('Ip address of ' + host + ' is ' + remote_ip)

# Given the instrument's computer name or IP address and socket port number now
# connect to the instrument remote server socket connection. At this point we
# are instantiating the instrument as an LAN SOCKET CONNECTION.
instrumentDirectSocket.connect((remote_ip , port))

print('Socket Connected to ' + host + ' on ip ' + remote_ip)

# ======================== Implement VNA-functions ============================

# ==========================================================================
# Function to initialize the instrument
def instrumentInit():
  
    try :
        # Clear the event status register and all prior errors in the queue
        instrumentDirectSocket.sendall(b"*CLS\n")
        
        # Reset instrument and via *OPC? hold-off for reset completion.
        instrumentDirectSocket.sendall(b"*RST;*OPC?\n")
        opComplete = instrumentDirectSocket.recv(8)
        #print "Operation complete detection = " + resetComplete
        
        # Assert a Identification query
        instrumentDirectSocket.sendall(b"*IDN?\n")
        idnResults = instrumentDirectSocket.recv(255)
        print("Identification results = " + str(idnResults))
        
    except socket.error:
        #Send failed
        print('Send failed')
        instrumentDirectSocket.exit()
    return;

# ==========================================================================
# Function to check the system error queue
def instrumentErrCheck():
   
    try :
        # Instrument error queues may store several errors. Loop and display all errors until 
        # no error indication
        
        errOutClear = -1
        noErrResult = b"NO ERROR"
         
        while (errOutClear < 0  ):
            instrumentDirectSocket.sendall(b"SYST:ERR?\n")
            errQueryResults = instrumentDirectSocket.recv(1024)
            print("Error query reults = " + str(errQueryResults))
            errQueryResultsUpper = errQueryResults.upper()
            errOutClear = errQueryResultsUpper.find(noErrResult)
    except socket.error:
        #Send failed
        print('Send failed')
        instrumentDirectSocket.exit()
    return;

# ==========================================================================
# A FUNCTION to configure the PNA.
# PNA configured to test transmission coefficient, S11
def instrumentSimplifiedSetup():                      #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    try :
        
        # Perform a factory preset with removal of all traces, windows, etc.
        instrumentDirectSocket.sendall(b"SYSTem:FPReset;*OPC?\n")
        opComplete = instrumentDirectSocket.recv(8)
        
        # Turn on Window 1
        instrumentDirectSocket.sendall(b"DISPlay:WINDow1:STATE ON\n")

        # Define a measurement name 'MyMeas' (a.k.a. label), 
        # and  a measurement parameter (e.g. S21, S11, or other)
        instrumentDirectSocket.sendall(b"CALCulate:PARameter:DEFine:EXT 'MyMeas',S11\n")
        
        #Associate ("FEED") the measurement name ('MyMeas') to WINDow (1), and give the new TRACe a number (1). 
        instrumentDirectSocket.sendall(b"DISPlay:WINDow1:TRACe1:FEED 'MyMeas'\n")
        
        # Set calibration
        instrumentDirectSocket.sendall(b"SENSe:CORRection:CSET:ACTivate " + bytes(calName,encoding='utf8') + b",1\n")
        
        # Set power level
        instrumentDirectSocket.sendall(b"SOURce:POWer:LEVel:IMMediate:AMPLitude " + bytes(str(powerLevel),encoding='utf8') + b"\n")
        
        # Set average ON or OFF
        instrumentDirectSocket.sendall(b"SENSe:AVERage:STATe OFF\n")
        #instrumentDirectSocket.sendall(b"SENSe:AVERage:COUNt 50\n")
        
        # Set center and span frequencies. 
        instrumentDirectSocket.sendall(b"SENS:FREQ:CENTer " +bytes(str(centerFrequency),encoding='utf8') +b";SPAN " +bytes(str(frequencySpan),encoding='utf8') +b"\n")
        #######instrumentDirectSocket.sendall(b";SPAN " + str(frequencySpan) + "\n")
        
        # Set number of sweep points 
        instrumentDirectSocket.sendall(b"SENSe1:SWEep:POINts "+bytes(str(sweepPoints),encoding='utf8')  +b"\n")
 
        #Set the bandwidth of the digital IF filter to be used in the measurement. 
        instrumentDirectSocket.sendall(b"SENSe1:BANDwidth:RESolution "+bytes(str(ifBandWidth),encoding='utf8') +b"\n")
        
        # Set format to log
        instrumentDirectSocket.sendall(b"CALCulate:MEASure:FORMat MLOGarithmic\n")
        
        # PNA requires all CALCulate sub commands to operate on a prior selected measurement name. 
        instrumentDirectSocket.sendall(b"CALCulate:PARameter:SELect 'MyMeas';*OPC?\n")
        opComplete = instrumentDirectSocket.recv(8)
              
    except socket.error: 
        #Send failed
        print('Send failed')
        instrumentDirectSocket.exit()
      
    return;
    
# ==========================================================================
# A FUNCTION to determine the returned array size. 
# Is it a one-dimensional x  numberOfpoints or 
# Is it a two-dimensional x numberOfPoints.

def determineDataArraySize():
    try :
        
       # All other formats beyond those listed below will return a one-dimensional x numPointsDataArray for FDATA
       #
       # Those formats returning 1x arrays are MLINear,MLOGarithmic,PHASe,UPHase 'Unwrapped phase,
       # IMAGinary,REAL,SWR,GDELay 'Group Delay,KELVin,FAHRenheit,CELSius. 
       #
       # Those FORMats returning    # 2x number of points data arrays (for FDATA query) are POLar,'
       # SMITh,'SADMittance 'Smith Admittance
       #
       # At current release only one-dimensional arrays, and their associated 'network analyzyer
       # formats are supported. 
       #
        instrumentDirectSocket.sendall(b"CALCulate1:FORMat?\n")  
        measSelectFormat =  instrumentDirectSocket.recv(64)
        if ((measSelectFormat.find(b"POL"))!=-1) :
            dataArraySize = 2 #dimension
        elif((measSelectFormat.find(b"SMIT"))!=-1) :
            dataArraySize = 2 #dimension
        elif((measSelectFormat.find(b"SADM"))!=-1) : 
            dataArraySize = 2 #dimension
        else:
            dataArraySize = 1

    except socket.error: 
        #Send failed
        print('Send failed')
        instrumentDirectSocket.exit()       
    
        return dataArraySize;

# ==========================================================================
# A function to query the response data array as an ASCII data transfer.

def getDataAsAsciiTransfer():
    
    try :
              
        instrumentDirectSocket.sendall(b"CALCulate1:DATA? FDATA\n")
        asciiDataArrayOut =  instrumentDirectSocket.recv(300000)
        print("Wait Time is " + str(waitTime))
        
        # A delay to accommodate LARGE data transfers via the socket port.
        # 
        # I found as the number of points in the sweep increases the data may be
        # corrupted due to SOCKETS timing and processing. 
        #
        # This occurs for both ASCII and BIN-Block transfers
        # Some PNAs can support 100,001 trace / sweep points. 
        #
        # The issue of dropped data bits surfaced for trace points in excess of
        # 201.This is NOT an acquisition timing issue. 
        # If the delay is too low for the number of points
        # the data is truncated and the Python Console will indicated an error similar to the following: 
            # floatDataArray.append(struct.unpack('d',instrumentDirectSocket.recv(8)))
            # error: unpack requires a string argument of length 8
            # Which basically indicates the format of the data has been corrupted and can not 
            # be parsed. 
        # The sleep timer is set at the beginning of the application and for low trace point counts
        # a value of 0 (seconds) should operate correctly. The sleep timer occurs in the following 
        # three functions:
                # getDataAsAsciiTransfer()
                # getDataAsBinBlockTransfer()
                # getStimulusArrayAsBinBlock()
        # I SEVERELY DISLIKE DELAYS IN ANY APPLICATION. However, I could not invest the time
        # to properly address the 'Whys?" of this dropped data issue. Future releases may 
        # rectify this issue. I suspect via an error handler and some form of a loop.
        #
        time.sleep(waitTime)
        print("The following data is an FDATA query result:")
        #print asciiDataArrayOut
        print("The asciiDataArrayOut lenght is "+ str(len(asciiDataArrayOut)))
    
    except socket.error: 
        #Send failed
        print('Send failed')
        instrumentDirectSocket.exit() 
        
    return asciiDataArrayOut;    

# ==========================================================================
# A FUNCTION to query the response data array as a binary bin-block real 64-bit data array.
def getDataAsBinBlockTransfer():
   
    # Float data array declaration
    # data will be a double as this is 8-bytes== 64-bits. 
    
    # Declare a floating or double array.    
    floatDataArray=[]

    # Set data transer format to efficient 64-bit real binary
    instrumentDirectSocket.sendall(b"FORMat:DATA REAL,64\n")
    
    # Control the byte order 
    instrumentDirectSocket.sendall(b"FORMat:BORDer SWAPPed;*OPC?\n")
    opComplete = instrumentDirectSocket.recv(8)

    # Now query bin-block FDATA - This is parsed manually. 
    instrumentDirectSocket.sendall(b"CALCulate1:DATA? FDATA\n")
    # First item returned on a bin-block is the '#' delimiter. Throw it away.
    junkHeader =  instrumentDirectSocket.recv(1)
    # The next single digit defines the number of digits to read next 
    # This will be 1 to 9.
    numOfDigitsToRead = instrumentDirectSocket.recv(1)
    
    # Determine how many bytes will be received based on
    # numOfDigitsToRead return value above.
    numOfBytes = instrumentDirectSocket.recv(int(numOfDigitsToRead))
   
    # A loop to read the number of Bytes returned. 
    # An example of a manually parsed real 64-bin binary bin-block data array read:
        # Data format set to Real 64-bin block transfer;
        # Trace format is set such a single one-dimensional data array is returned
        # The data query "CALCulate1:Data? FDATA\n" returns the following
        # If the number of sweep points was set to 11 then the following manual parse
        # '#288....the binaray data follows after.
            # '# is a default header - throw it away;
            # 2 is the next single character or digit read. It indicates
            # the next two characters define the size of the binary block transfer
            # The next two characters read are '88'.
            # For a display format with a single return data array and 11 points in the trace
            # each trace point is represented by a 64-bit, 8-byte real or float (double) -
            # 64-bit binary value. 11 points * 8 bytes per point = 88 bytes to follow as 
            # double real 64-bit values compliant with the IEEE-754 definition. 
            
    loopControl = 0
    for loopControl in range (0,int(int(numOfBytes)/8)):
        floatDataArray.append(struct.unpack('d',instrumentDirectSocket.recv(8)))
        
        loopControl +=1
    
    # Note of interest, below items due to one left less indent are outside of for loop
    # Read a hanging line feed. There is a line feed which must be serviced and thrown away
    # at the end of the binary bin-block data trasfer. 
    hangingLineFeed =  instrumentDirectSocket.recv(1)
    
    # A delay to accommodate LARGE data transfers via the socket port.
    # I found as the number of points in the sweep increases the data may be
    # corrupted due to SOCKETS timing and processing. 
    #
    # This occurs for both ASCII and BIN-Block
    # transfers. Some PNAs can support 20,000 points some to 100,000 points. 
    # The issue of dropped data bits surfaced for trace points in excess of
    # 201. 
    #
    # This is NOT an acquisition timing issue. If the delay is too low for the number of points
    # the data is truncated and the Python Console will indicated an error similar to the following: 
        # floatDataArray.append(struct.unpack('d',instrumentDirectSocket.recv(8)))
        # error: unpack requires a string argument of length 8
        # Which basically indicates the format of the data has been corrupted and can not 
        # be parsed. 
    # The sleep timer is set at the beginning of the application and for low trace point counts
    # a value of 0 (seconds) should operate correctly. The sleep timer occurs in the following 
    # three functions:
            # getDataAsAsciiTransfer()
            # getDataAsBinBlockTransfer()
            # getStimulusArrayAsBinBlock()
    # I SEVERELY DISLIKE DELAYS IN ANY APPLICATION. However, I could not invest the time
    # to properly address the 'Whys?" of this, me NOT being 
    time.sleep(waitTime)
    
    # Upon completion of BIN Block transfer return data transer to ASCII
    instrumentDirectSocket.sendall(b"FORMat:DATA ASCii,0;*OPC?\n")
    opComplete = instrumentDirectSocket.recv(8)


    #print "Bin BLOCK data array element values .............."
    return floatDataArray; 
 
    # ==========================================================================
# A FUNCTION to query the stimulus array as a Bin BLOCK real 64-bit binary array 
def getStimulusArrayAsBinBlock():
   
    # Float data array declaration
    # data will be a double as this is 8-bits == 64-bytes. 
    stimulusDataArray=[]
    
    numOfDigitsToRead = 0
    # Set data transer format to efficient 64-bit real binary
    instrumentDirectSocket.sendall(b"FORMat:DATA REAL,64\n")
    
    # Control the byte order 
    instrumentDirectSocket.sendall(b"FORMat:BORDer SWAPPed;*OPC?\n")
    opComplete = instrumentDirectSocket.recv(8) 
    
    # Now query bin-block Stimulus data array. This will be a manual parsing. 
    instrumentDirectSocket.sendall(b"SENSe1:X?\n")
    junkHeader =  instrumentDirectSocket.recv(1)
    numOfDigitsToRead = instrumentDirectSocket.recv(1)
    numOfBytes = instrumentDirectSocket.recv(int(numOfDigitsToRead))

    
    loopControl = 0
    for loopControl in range (0,int(int(numOfBytes)/8)):
        stimulusDataArray.append(struct.unpack('d',instrumentDirectSocket.recv(8)))

        loopControl +=1
    
    # Note of interest, below items due to  one left less indent are outside of for loop
    # Upon completion of BIN Block transfer return data transfer to ASCII
    
    # Read a hanging line feed
    hangingLineFeed =  instrumentDirectSocket.recv(1)
    instrumentDirectSocket.sendall(b"FORMat:DATA ASCii,0\n")
    
    return stimulusDataArray;
    
# ==========================================================================           
# A function to force a single trigger with auto-hold off via *OPC?
# a.k.a. the Operation Complete Query.

def triggerSingleWithHold():
    # Force a single trigger and hold-off for completions
    instrumentDirectSocket.sendall(b"SENse:SWEep:MODE SINGle;*OPC?\n")
    opComplete = instrumentDirectSocket.recv(8) 
    
    # Performs an Autoscale on the specified trace in the specified window, providing the best fit display.
    instrumentDirectSocket.sendall(b"DISPlay:WINDow1:TRACe1:Y:SCALe:AUTO;*OPC?\n")
    opComplete = instrumentDirectSocket.recv(8)
    
    #time.sleep(waitTime)
    
    return;
    
# ==========================================================================           
# A function to force trigger to continuous free-run.

def triggerFreeRun():
            # Force a single trigger and hold-off for completions
    instrumentDirectSocket.sendall(b"SENse:SWEep:MODE CONT;*OPC?\n")
    opComplete = instrumentDirectSocket.recv(8)
    
    return;
    
# ==========================================================================
# Saves s2p-file on VNA

def saveS2P(fileURL):
    instrumentDirectSocket.sendall(b"MMEMory:STORe '" + bytes(fileURL,encoding='utf8') + b"'\n")
    return True

# =============================================================================

# ========================= Implement libximc-library =========================

if sys.version_info >= (3,0):
    import urllib.parse

# Dependences
    
# For correct usage of the library libximc,
# you need to add the file pyximc.py wrapper with the structures of the library to python path.
cur_dir = os.path.abspath(os.path.dirname(__file__)) # Specifies the current directory.
ximc_dir = os.path.join(cur_dir, "..", "..", "..", "ximc") # Formation of the directory name with all dependencies. The dependencies for the examples are located in the ximc directory.
ximc_package_dir = os.path.join(ximc_dir, "crossplatform", "wrappers", "python") # Formation of the directory name with python dependencies.
sys.path.append(ximc_package_dir)  # add pyximc.py wrapper to python path

# Depending on your version of Windows, add the path to the required DLLs to the environment variable
# bindy.dll
# libximc.dll
# xiwrapper.dll
if platform.system() == "Windows":
    # Determining the directory with dependencies for windows depending on the bit depth.
    arch_dir = "win64" if "64" in platform.architecture()[0] else "win32" # 
    libdir = os.path.join(ximc_dir, arch_dir)
    if sys.version_info >= (3,8):
        os.add_dll_directory(libdir)
    else:
        os.environ["Path"] = libdir + ";" + os.environ["Path"] # add dll path into an environment variable

try: 
    from pyximc import *
except ImportError as err:
    print ("Can't import pyximc module. The most probable reason is that you changed the relative location of the test_Python.py and pyximc.py files. See developers' documentation for details.")
    exit()
except OSError as err:
    # print(err.errno, err.filename, err.strerror, err.winerror) # Allows you to display detailed information by mistake.
    if platform.system() == "Windows":
        if err.winerror == 193:   # The bit depth of one of the libraries bindy.dll, libximc.dll, xiwrapper.dll does not correspond to the operating system bit.
            print("Err: The bit depth of one of the libraries bindy.dll, libximc.dll, xiwrapper.dll does not correspond to the operating system bit.")
            # print(err)
        elif err.winerror == 126: # One of the library bindy.dll, libximc.dll, xiwrapper.dll files is missing.
            print("Err: One of the library bindy.dll, libximc.dll, xiwrapper.dll is missing.")
            print("It is also possible that one of the system libraries is missing. This problem is solved by installing the vcredist package from the ximc\\winXX folder.")
            # print(err)
        else:           # Other errors the value of which can be viewed in the code.
            print(err)
        print("Warning: If you are using the example as the basis for your module, make sure that the dependencies installed in the dependencies section of the example match your directory structure.")
        print("For correct work with the library you need: pyximc.py, bindy.dll, libximc.dll, xiwrapper.dll")
    else:
        print(err)
        print ("Can't load libximc library. Please add all shared libraries to the appropriate places. It is decribed in detail in developers' documentation. On Linux make sure you installed libximc-dev package.\nmake sure that the architecture of the system and the interpreter is the same")
    exit()

# ========================= Implement motor-functions =========================

def test_info(lib, device_id):
    print("\nGet device info")
    x_device_information = device_information_t()
    result = lib.get_device_information(device_id, byref(x_device_information))
    print("Result: " + repr(result))
    if result == Result.Ok:
        print("Device information:")
        print(" Manufacturer: " +
                repr(string_at(x_device_information.Manufacturer).decode()))
        print(" ManufacturerId: " +
                repr(string_at(x_device_information.ManufacturerId).decode()))
        print(" ProductDescription: " +
                repr(string_at(x_device_information.ProductDescription).decode()))
        print(" Major: " + repr(x_device_information.Major))
        print(" Minor: " + repr(x_device_information.Minor))
        print(" Release: " + repr(x_device_information.Release))

def test_status(lib, device_id):
    print("\nGet status")
    x_status = status_t()
    result = lib.get_status(device_id, byref(x_status))
    print("Result: " + repr(result))
    if result == Result.Ok:
        print("Status.Ipwr: " + repr(x_status.Ipwr))
        print("Status.Upwr: " + repr(x_status.Upwr))
        print("Status.Iusb: " + repr(x_status.Iusb))
        print("Status.Flags: " + repr(hex(x_status.Flags)))

def test_get_position(lib, device_id):
    print("\nRead position")
    x_pos = get_position_t()
    result = lib.get_position(device_id, byref(x_pos))
    print("Result: " + repr(result))
    if result == Result.Ok:
        print("Position: {0} steps, {1} microsteps".format(x_pos.Position, x_pos.uPosition))
    return x_pos.Position, x_pos.uPosition

def test_left(lib, device_id):
    print("\nMoving left")
    result = lib.command_left(device_id)
    print("Result: " + repr(result))

def test_move(lib, device_id, distance, udistance):
    print("\nGoing to {0} steps, {1} microsteps".format(distance, udistance))
    result = lib.command_move(device_id, distance, udistance)
    print("Result: " + repr(result))

def test_wait_for_stop(lib, device_id, interval):
    print("\nWaiting for stop")
    result = lib.command_wait_for_stop(device_id, interval)
    print("Result: " + repr(result))

def test_serial(lib, device_id):
    print("\nReading serial")
    x_serial = c_uint()
    result = lib.get_serial_number(device_id, byref(x_serial))
    if result == Result.Ok:
        print("Serial: " + repr(x_serial.value))

def test_get_speed(lib, device_id)        :
    print("\nGet speed")
    # Create move settings structure
    mvst = move_settings_t()
    # Get current move settings from controller
    result = lib.get_move_settings(device_id, byref(mvst))
    # Print command return status. It will be 0 if all is OK
    print("Read command result: " + repr(result))    
    
    return mvst.Speed
        
def test_set_speed(lib, device_id, speed):
    print("\nSet speed")
    # Create move settings structure
    mvst = move_settings_t()
    # Get current move settings from controller
    result = lib.get_move_settings(device_id, byref(mvst))
    # Print command return status. It will be 0 if all is OK
    print("Read command result: " + repr(result))
    print("The speed was equal to {0}. We will change it to {1}".format(mvst.Speed, speed))
    # Change current speed
    mvst.Speed = int(speed)
    # Write new move settings to controller
    result = lib.set_move_settings(device_id, byref(mvst))
    # Print command return status. It will be 0 if all is OK
    print("Write command result: " + repr(result))    
    

def test_set_microstep_mode_256(lib, device_id):
    print("\nSet microstep mode to 256")
    # Create engine settings structure
    eng = engine_settings_t()
    # Get current engine settings from controller
    result = lib.get_engine_settings(device_id, byref(eng))
    # Print command return status. It will be 0 if all is OK
    print("Read command result: " + repr(result))
    # Change MicrostepMode parameter to MICROSTEP_MODE_FRAC_256
    # (use MICROSTEP_MODE_FRAC_128, MICROSTEP_MODE_FRAC_64 ... for other microstep modes)
    eng.MicrostepMode = MicrostepMode.MICROSTEP_MODE_FRAC_256
    # Write new engine settings to controller
    result = lib.set_engine_settings(device_id, byref(eng))
    # Print command return status. It will be 0 if all is OK
    print("Write command result: " + repr(result))    

# ========================== Connecting to motor ==============================

# variable 'lib' points to a loaded library
# note that ximc uses stdcall on win
print("Library loaded")

sbuf = create_string_buffer(64)
lib.ximc_version(sbuf)
print("Library version: " + sbuf.raw.decode().rstrip("\0"))

# Set bindy (network) keyfile. Must be called before any call to "enumerate_devices" or "open_device" if you
# wish to use network-attached controllers. Accepts both absolute and relative paths, relative paths are resolved
# relative to the process working directory. If you do not need network devices then "set_bindy_key" is optional.
# In Python make sure to pass byte-array object to this function (b"string literal").
result = lib.set_bindy_key(os.path.join(ximc_dir, "win32", "keyfile.sqlite").encode("utf-8"))
if result != Result.Ok:
    lib.set_bindy_key("keyfile.sqlite".encode("utf-8")) # Search for the key file in the current directory.

# This is device search and enumeration with probing. It gives more information about devices.
probe_flags = EnumerateFlags.ENUMERATE_PROBE + EnumerateFlags.ENUMERATE_NETWORK
enum_hints = b"addr="
# enum_hints = b"addr=" # Use this hint string for broadcast enumerate
devenum = lib.enumerate_devices(probe_flags, enum_hints)
print("Device enum handle: " + repr(devenum))
print("Device enum handle type: " + repr(type(devenum)))

dev_count = lib.get_device_count(devenum)
print("Device count: " + repr(dev_count))

controller_name = controller_name_t()
for dev_ind in range(0, dev_count):
    enum_name = lib.get_device_name(devenum, dev_ind)
    result = lib.get_enumerate_device_controller_name(devenum, dev_ind, byref(controller_name))
    if result == Result.Ok:
        print("Enumerated device #{} name (port name): ".format(dev_ind) + repr(enum_name) + ". Friendly name: " + repr(controller_name.ControllerName) + ".")

flag_virtual = 0

open_name = None
if len(sys.argv) > 1:
    open_name = sys.argv[1]
elif dev_count > 0:
    open_name = lib.get_device_name(devenum, 1) ######### 0 or 1 is device number
elif sys.version_info >= (3,0):
    # use URI for virtual device when there is new urllib python3 API
    tempdir = tempfile.gettempdir() + "/testdevice.bin"
    if os.altsep:
        tempdir = tempdir.replace(os.sep, os.altsep)
    # urlparse build wrong path if scheme is not file
    uri = urllib.parse.urlunparse(urllib.parse.ParseResult(scheme="file", \
            netloc=None, path=tempdir, params=None, query=None, fragment=None))
    open_name = re.sub(r'^file', 'xi-emu', uri).encode()
    flag_virtual = 1
    print("The real controller is not found or busy with another app.")
    print("The virtual controller is opened to check the operation of the library.")
    print("If you want to open a real controller, connect it or close the application that uses it.")

if not open_name:
    exit(1)

if type(open_name) is str:
    open_name = open_name.encode()

print("\nOpen device " + repr(open_name))
device_id = lib.open_device(open_name)
print("Device id: " + repr(device_id))

# =============================================================================
# =============================================================================
# Do individual measurement

def measurement():
    test_info(lib, device_id)
    test_status(lib, device_id)
    test_set_microstep_mode_256(lib, device_id)
    test_set_speed(lib, device_id, 250)
    test_move(lib, device_id, 0, 0)
    test_wait_for_stop(lib, device_id, 100)
    startpos, ustartpos = test_get_position(lib, device_id)
    
    for i in range(17):
        test_move(lib, device_id, -1000*i, 0)
        test_wait_for_stop(lib, device_id, 100)
        saveS2P("d:/Nils/meas_" + str(1000*i) + ".s2p")
        time.sleep(3)
    
    test_move(lib, device_id, 0, 0)
    test_wait_for_stop(lib, device_id, 100)
    return True

# =============================================================================
# =============================================================================



# ================================ MAIN =======================================
# THis is the "MAIN" where all the functions are invoked.    
   
# FUNCTION CALL _ instrumentInit function call
instrumentInit()

# FUNCTION CALL _  instrumentInitErrorChecck call
instrumentErrCheck()

# FUNCTION CALL _  instrumentSimplifiedSetup funciton call
instrumentSimplifiedSetup()

'''
# FUNCTION CALL _  determineDataArraySize call
dataArraySize = determineDataArraySize()

# FUNCTION CALL _  triggerSingleWithHold call
triggerSingleWithHold()

# FUNCTION CALL _  getDataAsAsciiTransfer call
dataArrayAsAscii = getDataAsAsciiTransfer()
print(dataArrayAsAscii)

# FUNCTION CALL _  getDataAsBinBLockTransfer call
floatDataArray = getDataAsBinBlockTransfer()
print("Response array as acquired as binary bin-block transfer\n")
print(floatDataArray)

# FUNCTION CALL _  getStimulusArrayAsBinBlock call
stimulusDataArray = getStimulusArrayAsBinBlock()
print("Stimulus array as acquired as binary bin-block transer\n")
print(stimulusDataArray)
'''

# Trigger back to free run continuous call
triggerFreeRun()



measurement()



# close the socket on completion. 
instrumentDirectSocket.close()

'''
# Plot results with stimulus and response arrays (from bin block calls)
plot(stimulusDataArray,floatDataArray)
 
xlabel('Frequency')
ylabel('dB')
title('S11 Formatted Data')
grid(True)
show()
'''



print("\nClosing")

# The device_t device parameter in this function is a C pointer, unlike most library functions that use this parameter
lib.close_device(byref(cast(device_id, POINTER(c_int))))
print("Done")

if flag_virtual == 1:
    print(" ")
    print("The real controller is not found or busy with another app.")
    print("The virtual controller is opened to check the operation of the library.")
    print("If you want to open a real controller, connect it or close the application that uses it.")
    
# ================================ MAIN =======================================
