from __future__ import print_function
from threading import Thread
from email.utils import parsedate
from time import sleep
from socket import error as socket_error


class Communicator(Thread):

    #this list contains all implemented smtp commands
    smtp_commands = ["helo", "mail", "rcpt", "data", "quit", "help"]
    codes = {
            "220": "220 Welcome to meap - mailing easy as pie - smtp server! Service ready.\r\n",
            "221": "221 OK I will close the connection. Have a nice day!\r\n",
            "250": "250 OK I received the email.\r\n",
            "354": "354 Send the mail data and terminate with <CRLF>.<CRLF>\r\n",
            "500": "500 Syntax error, I don't know that command.\r\n",
            "501": "501 Syntax error in the parameter.\r\n",
            "503": "503 Wrong sequence of commands.\r\n",
            }

    def __init__(self, com):
        Thread.__init__(self)
        self.com = com
        self.smtp_state = None
        self.sender = ""
        self.receiver = []
        self.email = ""

    def run(self):
        self.process()

    def process(self):
        """
        this method handles the whole communication with the client
        """
        try:
            self.com_send(self.codes['220'])
            while True:
                if self.smtp_state == "data":
                    self.email = self.com.recv(512).decode("utf-8")
                    while not "\r\n.\r\n" in self.email:
                        self.email += self.com.recv(512)
                    print ("Received: %s " % repr(self.email)[1:-1])
                    if not self.check_email():
                        self.email = ""
                        self.com_send("501 Error in email header.\r\n")
                        self.smtp_state = "rcpt"
                        continue
                    self.com_send(self.codes["250"])
                    self.store_email()
                    # clean up
                    self.smtp_state = "helo"
                    self.sender = ""
                    self.receiver = []
                    self.email = ""
                    continue

                data = self.get_data()

                command = self.check_command(data)
                if not command:
                    self.com_send(self.codes["500"])
                    continue

                param = None
                if len(data) > 4:
                    param = data[4:].strip()

                if command == "help":
                    self.com_send("214 Let me help you, I understand the following SMTP commands:\r\n"
                             "HELO - tell me your name\r\n"
                             "MAIL - tell me the sender\r\n"
                             "RCPT - tell me the receiver\r\n"
                             "DATA - tell me that you wants to send mail data\r\n"
                             "QUIT - tell me that you wants to leave me\r\n"
                             "HELP - get this help\r\n")
                    continue

                if command == "helo":
                    self.com_send("250 Hello %s! Nice to meet you!\r\n" % param)
                    self.smtp_state = "helo"
                    continue

                if command == "quit":
                    self.com_send(self.codes["221"])
                    sleep(0.5)
                    self.com.close()
                    return

                if command == "mail":
                    if self.smtp_state == "helo":
                        if param:
                            param_proc = str(param).replace(" ", "").lower()
                            if param_proc.startswith("from:<") and param_proc.endswith(">"):
                                self.sender = param_proc[6:-1]
                                self.com_send("250 OK\r\n")
                                self.smtp_state = "mail"
                                continue
                            else:
                                self.com_send(self.codes["501"])
                                continue
                        else:
                            self.com_send(self.codes["501"])
                            continue
                    else:
                        self.com_send(self.codes["503"])
                        continue

                if command == "rcpt":
                    if self.smtp_state == "mail" or self.smtp_state == "rcpt":
                        if param:
                            param_proc = str(param).replace(" ", "").lower()
                            if param_proc.startswith("to:<") and param_proc.endswith(">"):
                                self.receiver.append(param_proc[4:-1])
                                self.com_send("250 OK\r\n")
                                self.smtp_state = "rcpt"
                                continue
                            else:
                                self.com_send(self.codes["501"])
                                continue
                        else:
                            self.com_send(self.codes["501"])
                            continue
                    else:
                        self.com_send(self.codes["503"])
                        continue

                if command == "data":
                    if self.smtp_state == "rcpt":
                        self.com_send(self.codes["354"])
                        self.smtp_state = "data"
                        continue
                    else:
                        self.com_send(self.codes["503"])
                        continue

        except socket_error:
            print("Lost connection to the client.")
            return

    def get_data(self):
        """
        reads the data from the socket and removes control symbols
        :return: the received data
        """
        data = self.com.recv(512).decode("utf-8")
        if not data.endswith('\r\n'):
            data += self.com.recv(512)
        print ("Received: %s " % repr(data)[1:-1])
        data = data.replace('\r', '').replace('\n', '')
        return data

    def com_send(self, response):
        """
        sends the response to the client and prints it on the console
        :param reply: the response
        """
        print("Response: " + response)
        self.com.send(bytes(response, "utf-8"))

    def check_command(self, message):
        """
        checks if the received message starts with a valid smtp command
        :param message: the received message from the client
        :return: the received smtp command or False
        """
        command = False
        if len(message) >= 4:
            if message[:4].lower() in Communicator.smtp_commands:
                command = message[:4].lower()
        return command

    def check_email(self):
        """
        checks if from, to, subject and date fields are present in email header
        this is not required in smtp but used for test purposes
        :return: True when the above 4 header fields are presnent, if not False
        """
        head_from = False
        head_to = False
        head_subject = False
        head_date = False
        email_lines = self.email.split('\r\n')
        for line in email_lines:
            line = line.lower()
            if line.startswith("from:"):
                head_from = True
            if line.startswith("to:"):
                head_to = True
            if line.startswith("subject:"):
                head_subject = True
            if line.startswith("date:"):
                if not parsedate(line[5:]) is None:
                    head_date = True
        if head_from and head_to and head_subject and head_date:
            return True
        return False

    def store_email(self):
        """
        stores the email in a text file with the name [receiver]-emails.txt
        """
        for receiver in self.receiver:
            f = open(receiver + "-emails.txt", 'a')
            print("FROM: " + self.sender + "\r\n" + self.email + "----------", file=f)
            f.close()