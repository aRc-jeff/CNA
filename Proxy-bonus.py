##################################################
#Extension 1:
#Added checking for Expires header into the same logic block that handled max-age.
#Code will check for the header entry, decode the timestamp and check if the timestamp has passed.
#A flag will be raised if the cache is expired and an exception raised that the cache expired, 
#resulting in the request being fetched from the origin server
#
#Extension 2:
#Added logic to extract all href and src assets using regular expressions filling a list
#Might implement the requesting a caching if I get time, would require significant restructuring of code
#
#Extension 3:
#Added logic to split the hostname around the : into a hostname and a hostport (defaults to 80).
#Previously host port was hardcoded at 80, replaced with host port variable
##################################################

# Include the libraries for socket and system calls
import socket
import sys
import os
import argparse
import re
import traceback
import datetime

# 1MB buffer size
BUFFER_SIZE = 1000000

# debug mode
debug = False

# Get the IP address and Port number to use for this web proxy server
parser = argparse.ArgumentParser()
parser.add_argument('hostname', help='the IP Address Of Proxy Server')
parser.add_argument('port', help='the port number of the proxy server')
args = parser.parse_args()
proxyHost = args.hostname
proxyPort = int(args.port)

# Create a server socket, bind it to a port and start listening
try:
  # Create a server socket
  # ~~~~ INSERT CODE ~~~~
  serverSocket = socket.socket() #im pretty sure these are both default values
  # ~~~~ END CODE INSERT ~~~~
  print ('Created socket')
except:
  if debug: print(traceback.format_exc())
  print ('Failed to create socket')
  sys.exit()

try:
  # Bind the the server socket to a host and port
  # ~~~~ INSERT CODE ~~~~
  serverSocket.bind(('',proxyPort))
  # ~~~~ END CODE INSERT ~~~~
  print ('Port is bound')
except:
  if debug: print(traceback.format_exc())
  print('Port is already in use')
  sys.exit()

try:
  # Listen on the server socket
  # ~~~~ INSERT CODE ~~~~
  serverSocket.listen(1)
  # ~~~~ END CODE INSERT ~~~~
  print ('Listening to socket')
except:
  if debug: print(traceback.format_exc())
  print ('Failed to listen')
  sys.exit()

# continuously accept connections
while True:
  print ('Waiting for connection...')
  clientSocket = None

  # Accept connection from client and store in the clientSocket
  try:
    # ~~~~ INSERT CODE ~~~~
    (clientSocket, addr) = serverSocket.accept()
    # ~~~~ END CODE INSERT ~~~~
    print ('Received a connection')
  except:
    if debug: print(traceback.format_exc())
    print ('Failed to accept connection')
    sys.exit()

  # Get HTTP request from client
  # and store it in the variable: message_bytes
  # ~~~~ INSERT CODE ~~~~
  message_bytes = clientSocket.recv(BUFFER_SIZE)
  # ~~~~ END CODE INSERT ~~~~
  message = message_bytes.decode('utf-8')
  print ('Received request:')
  print ('< ' + message)

  # Extract the method, URI and version of the HTTP client request 
  requestParts = message.split()
  method = requestParts[0]
  URI = requestParts[1]
  version = requestParts[2]

  print ('Method:\t\t' + method)
  print ('URI:\t\t' + URI)
  print ('Version:\t' + version)
  print ('')

  # Get the requested resource from URI
  # Remove http protocol from the URI
  URI = re.sub('^(/?)http(s?)://', '', URI, count=1)

  # Remove parent directory changes - security
  URI = URI.replace('/..', '')

  # Split hostname from resource name
  resourceParts = URI.split('/', 1)
  host = resourceParts[0]
  #check if the host includes a port
  if ":" in host:
    #split the host into hostname and port
    hostPort = host[(host.find(":")+1):]
    hostname = host[:(host.find(":"))]
  else:
    #default port to 80
    hostPort = "80"
    hostname = host
  resource = '/'

  if len(resourceParts) == 2:
    # Resource is absolute URI with hostname and resource
    resource = resource + resourceParts[1]

  print ('Requested Resource:\t' + resource)

  # Check if resource is in cache
  try:
    cacheLocation = './' + hostname + resource
    if cacheLocation.endswith('/'):
        cacheLocation = cacheLocation + 'default'

    print ('Cache location:\t\t' + cacheLocation)

    fileExists = os.path.isfile(cacheLocation)
    
    # Check wether the file is currently in the cache
    cacheFile = open(cacheLocation, "rb")
    cacheData = cacheFile.readlines()
    cacheData = [item.decode() for item in cacheData]

    print ('Cache hit! Loading from cache file: ' + cacheLocation)
    # ProxyServer finds a cache hit
    # Send back response to client 
    # ~~~~ INSERT CODE ~~~~
    #for max-age
    cacheExpires = False
    #for expires
    cacheExpired = False
    #loop to check headers
    for item in cacheData:
        #response to cache control headers
        if item.startswith("Cache-Control:"):
          itemFields = item.split()
          #find max-age=
          for field in itemFields:
            if field.startswith("max-age="):
              #save max age value and raise expiry flag
              maxAge = int(field[field.find("=")+1:])
              cacheExpires = True
        #find the timestamp of the cache
        if item.startswith("Date:"):
          timestampStr = item[item.find(" ")+1:].strip()
          timestamp = datetime.datetime.strptime(timestampStr, "%a, %d %b %Y %H:%M:%S %Z")
          timestamp = timestamp.replace(tzinfo=datetime.UTC)
          currTimestamp = datetime.datetime.now(datetime.UTC)
          timeElapsed = (currTimestamp-timestamp).total_seconds()
        if item.startswith("Expires:"):
          timestampStr = item[item.find(" ")+1:].strip()
          #this call throws an exception when expires does not have a datestamp (like -1)
          #this will result in the file being fetched from the origin server. This is expected behaviour
          timestamp = datetime.datetime.strptime(timestampStr, "%a, %d %b %Y %H:%M:%S %Z")
          timestamp = timestamp.replace(tzinfo=datetime.UTC)
          currTimestamp = datetime.datetime.now(datetime.UTC)
          if currTimestamp > timestamp:
            cacheExpired = True
            cacheExpires = True          

    #raise exception if max age is exceeded (exception results in fetching from origin)
    #or should short circuit and not check time elapsed and max age when they are not defined
    #won't check either unless cacheExpires is true
    if (cacheExpires and (cacheExpired or (timeElapsed > maxAge))):
      raise Exception("Cache Expired") 
    
    #send cache data
    cacheData = "".join(cacheData)
    clientSocket.sendall(cacheData.encode())
    # ~~~~ END CODE INSERT ~~~~
    cacheFile.close()
    print ('Sent to the client:')
    print ('> ' + cacheData)
  except:
    if debug: print(traceback.format_exc())
    # cache miss.  Get resource from origin server
    originServerSocket = None
    # Create a socket to connect to origin server
    # and store in originServerSocket
    # ~~~~ INSERT CODE ~~~~
    originServerSocket = socket.socket()
    # ~~~~ END CODE INSERT ~~~~

    print ('Connecting to:\t\t' + hostname + '\n')
    try:
      # Get the IP address for a hostname
      address = socket.gethostbyname(hostname)
      # Connect to the origin server
      # ~~~~ INSERT CODE ~~~~
      #conncect to origin server with address and hostPort
      originServerSocket.connect((address, int(hostPort)))
      # ~~~~ END CODE INSERT ~~~~
      print ('Connected to origin Server')

      originServerRequest = ''
      originServerRequestHeader = ''
      # Create origin server request line and headers to send
      # and store in originServerRequestHeader and originServerRequest
      # originServerRequest is the first line in the request and
      # originServerRequestHeader is the second line in the request
      # ~~~~ INSERT CODE ~~~~
      #complie message line
      originServerRequest = method + ' ' + resource + ' ' + version
      #split lines from the message, removing the first line as it is th request line
      headers = message.splitlines()
      headers = headers[1:]
      #correct the hostname header
      for i, item in enumerate(headers):
        if item.startswith("Host:"):
          #include hostPort in header
          headers[i] = "Host: " + hostname + ":" + hostPort
      #build the headers 
      originServerRequestHeader = "\n".join(headers)
      # ~~~~ END CODE INSERT ~~~~

      # Construct the request to send to the origin server
      request = originServerRequest + '\r\n' + originServerRequestHeader + '\r\n\r\n'

      # Request the web resource from origin server
      print ('Forwarding request to origin server:')
      for line in request.split('\r\n'):
        print ('> ' + line)

      try:
        originServerSocket.sendall(request.encode())
      except socket.error:
        if debug: print(traceback.format_exc())
        print ('Forward request to origin failed')
        sys.exit()

      print('Request sent to origin server\n')

      # Get the response from the origin server
      # ~~~~ INSERT CODE ~~~~
      #Receive data from origin server
      response = originServerSocket.recv(BUFFER_SIZE)
      #since for larger messages sometimes recv doesnt get the whole message (returns whatever is in the buffer, not necessarily the whole msg)
      #next code chunk breaks up the response to find the headers, find the content-length header and continue to recieve data until the message is the right length
      #first CRLF before header
      p0 = response.find(b"\r\n")
      #CRLF CRLF after header
      p1 = response.find(b"\r\n\r\n")
      #split out the headers
      responseHeader = response[(p0+len(b"\r\n")):(p1 + len(b"\r\n"))]
      responseHeader = responseHeader.decode('utf-8')
      responseHeader = responseHeader.splitlines()
      contentLengthDefined = False
      #find the content length header and determine the length of the msg
      for item in responseHeader:
        if item.startswith("Content-Length:"):
          contentLength = int(item[(item.find(" ")+1):])
          contentLengthDefined = True
      #loop recv untill all the message is recieved
      if contentLengthDefined:
        while len(response) < (contentLength + p1 + len(b"\r\n\r\n")):
          response += originServerSocket.recv(BUFFER_SIZE)
      #split out the status line and isolate the statusCode
      statusLine = response[:p0]
      statusElements = statusLine.split()
      statusCode = statusElements[1]
      # ~~~~ END CODE INSERT ~~~~

      # Send the response to the client
      # ~~~~ INSERT CODE ~~~~
      clientSocket.sendall(response)

      #find all src and href assets in the message body and build a list to cache
      src = rb'src=["\'](.*?)["\']'
      srcMatches = re.findall(src, response[p1:], re.IGNORECASE)
      href = rb'href=["\'](.*?)["\']'
      hrefMatches = re.findall(href, response[p1:], re.IGNORECASE)
      objects = [match.decode() for match in srcMatches] + [match.decode() for match in hrefMatches]
      # ~~~~ END CODE INSERT ~~~~
      #only try to cache codes that are cacheable (according to rfc)
      cacheableCodes = [b"200", b"203", b"206", b"300", b"301", b"410"]
      if statusCode in cacheableCodes:
        #This if statement stops the server caching if no-store is specified
        if not "Cache-Control: no-store" in responseHeader:
          #try except to catch issue with invalid file directories in the cache
          try:
            # Create a new file in the cache for the requested file.
            cacheDir, file = os.path.split(cacheLocation)
            print ('cached directory ' + cacheDir)
            if not os.path.exists(cacheDir):
              os.makedirs(cacheDir)
            cacheFile = open(cacheLocation, 'wb')

            # Save origin server response in the cache file
            # ~~~~ INSERT CODE ~~~~
            cacheFile.write(response)
            # ~~~~ END CODE INSERT ~~~~
            cacheFile.close()
            print ('cache file closed')
          except OSError as err:
            print ('Cache Failed. ' + err.strerror) #windows doesn't allow ? in file directory
      # finished communicating with origin server - shutdown socket writes
      print ('origin response received. Closing sockets')
      originServerSocket.close()
       
      clientSocket.shutdown(socket.SHUT_WR)
      print ('client socket shutdown for writing')
    except OSError as err:
      if debug: print(traceback.format_exc())
      print ('origin server request failed. ' + err.strerror)

  try:
    clientSocket.close()
  except:
    if debug: print(traceback.format_exc())
    print ('Failed to close client socket')
