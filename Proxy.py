# Include the libraries for socket and system calls
import socket
import sys
import os
import argparse
import re
import traceback
import time
import datetime

# 1MB buffer size
BUFFER_SIZE = 1000000

# debug mode
debug = True

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
  hostname = resourceParts[0]
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
    cacheFile = open(cacheLocation, "r")
    cacheData = cacheFile.readlines()

    print ('Cache hit! Loading from cache file: ' + cacheLocation)
    # ProxyServer finds a cache hit
    # Send back response to client 
    # ~~~~ INSERT CODE ~~~~
    cacheExpires = False
    for item in cacheData:
        if item.startswith("Cache-Control:"):
          itemFields = item.split()
          for field in itemFields:
            if field.startswith("max-age="):
              maxAge = int(field[field.find("=")+1:])
              cacheExpires = True
        if item.startswith("Date:"):
          timestampStr = item[item.find(" ")+1:].strip()
          timestamp = datetime.datetime.strptime(timestampStr, "%a, %d %b %Y %H:%M:%S %Z")
          timestamp = timestamp.replace(tzinfo=datetime.UTC)
          currTimestamp = datetime.datetime.now(datetime.UTC)
          timeElapsed = (currTimestamp-timestamp).total_seconds()

    if (cacheExpires and (timeElapsed > maxAge)):
      raise Exception("Cache Expired") 
       
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
      originServerSocket.connect((address, 80))
      # ~~~~ END CODE INSERT ~~~~
      print ('Connected to origin Server')

      originServerRequest = ''
      originServerRequestHeader = ''
      # Create origin server request line and headers to send
      # and store in originServerRequestHeader and originServerRequest
      # originServerRequest is the first line in the request and
      # originServerRequestHeader is the second line in the request
      # ~~~~ INSERT CODE ~~~~
      originServerRequest = method + ' ' + resource + ' ' + version
      headers = message.splitlines()
      headers = headers[1:]
      for i, item in enumerate(headers):
        if item.startswith("Host:"):
          headers[i] = "Host: " + hostname + ":" + "80"
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
      response = originServerSocket.recv(BUFFER_SIZE)
      p0 = response.find(b"\r\n")
      p1 = response.find(b"\r\n\r\n")
      responseHeader = response[(p0+len(b"\r\n")):(p1 + len(b"\r\n"))]
      responseHeader = responseHeader.decode('utf-8')
      responseHeader = responseHeader.splitlines()
      contentLengthDefined = False
      for item in responseHeader:
        if item.startswith("Content-Length:"):
          contentLength = int(item[(item.find(" ")+1):])
          contentLengthDefined = True
      if contentLengthDefined:
        while len(response) < (contentLength + p1 + len(b"\r\n\r\n")):
          response += originServerSocket.recv(BUFFER_SIZE)
      statusLine = response[:p0]
      statusElements = statusLine.split()
      statusCode = statusElements[1]
      # ~~~~ END CODE INSERT ~~~~

      # Send the response to the client
      # ~~~~ INSERT CODE ~~~~
      clientSocket.sendall(response)
      # ~~~~ END CODE INSERT ~~~~
      #should probably only cache OK's
      if statusCode == b"200":
        #This if statement stops the server caching if no-store is specified
        if not "Cache-Control: no-store" in responseHeader:
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
