import socket
import sys
from communicator import Communicator

HOST = ''                 # listen on all interfaces
PORT = 25                 # SMTP default port
if len(sys.argv) == 2:
    PORT = sys.argv[1]    # take port from param list if given

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))

print "meap smtp server running on port %d" % PORT

while True:
    s.listen(1)
    con, addr = s.accept()
    print "Connected by Client: " + str(addr)
    Communicator(con).start()