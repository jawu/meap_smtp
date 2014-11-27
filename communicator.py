from __future__ import print_function
from threading import Thread
from email.utils import parsedate
from time import sleep


class Communicator(Thread):

    smtp_commands = ["helo", "mail", "rcpt", "data", "quit", "help"]

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
        self.com_send("220 Welcome to meap - mailing easy as pie - smtp server! Service ready.\r\n")
        while True:
            if self.smtp_state == "data":
                self.email = self.com.recv(512)
                while not "\r\n.\r\n" in self.email:
                    self.email += self.com.recv(512)
                print ("Received: %s " % repr(self.email)[1:-1])
                if not self.check_email():
                    self.email = ""
                    self.com_send("501 Error in email header.\r\n")
                    self.smtp_state = "rcpt"
                    continue
                self.com_send("250 OK I received the email.\r\n")
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
                self.com_send("500 Syntax error, I don't know that command.\r\n")
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
                self.com_send("221 OK I will close the connection. Have a nice day!\r\n")
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
                            self.com_send("501 Syntax error in the parameter.\r\n")
                            continue
                    else:
                        self.com_send("501 Syntax error in the parameter.\r\n")
                        continue
                else:
                    self.com_send("503 Wrong sequence of commands.\r\n")
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
                            self.com_send("501 Syntax error in the parameter.\r\n")
                            continue
                    else:
                        self.com_send("501 Syntax error in the parameter.\r\n")
                        continue
                else:
                    self.com_send("503 Wrong sequence of commands.\r\n")
                    continue

            if command == "data" and self.smtp_state == "rcpt":
                self.com_send("354 Send the mail data and terminate with <CRLF>.<CRLF>\r\n")
                self.smtp_state = "data"
                continue

            self.com_send("503 Wrong sequence of commands.\r\n")
            continue

    def get_data(self):
        data = self.com.recv(512)
        if not data.endswith('\r\n'):
            data += self.com.recv(512)
        print ("Received: %s " % repr(data)[1:-1])
        data = data.replace('\r', '').replace('\n', '')
        if not data:
            data = self.get_data()
        return data

    def com_send(self, reply):
        print("Response: " + reply)
        self.com.send(reply)

    def check_command(self, message):
        command = False
        if len(message) >= 4:
            if message[:4].lower() in Communicator.smtp_commands:
                command = message[:4].lower()
        return command

    def check_email(self):
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
        for receiver in self.receiver:
            f = open(receiver + "-emails.txt", 'a')
            print("FROM: " + self.sender + "\r\n" + self.email + "----------", file=f)
            f.close()