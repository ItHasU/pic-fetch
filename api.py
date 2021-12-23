import configparser
import email
from email.header import decode_header
import imaplib
import smtplib
from typing import Callable
import quopri

PARAMS_SERVER = "Server"
PARAMS_USER = "Username"
PARAMS_PASS = "Password"

PARAMS_IMAP_MAX_MESSAGES = "MaxMessagesCount"
PARAMS_ADMIN_EMAIL = "email"

# This class provides all the function necessary to read/send emails.
# It is initialized from a configuration file (by default config.ini)
class MailManager:
    def __init__(self, config: configparser.ConfigParser) -> None:
        self._callbacks = {}
        self._default_callback = None

        # Read global configuration
        admin_config = config["ADMIN"]
        self._admin_email = admin_config[PARAMS_ADMIN_EMAIL]

        # Read imap configuration
        imap_config = config["IMAP"]
        self._imap_server = imap_config[PARAMS_SERVER]
        self._imap_username = imap_config[PARAMS_USER]
        self._imap_password = imap_config[PARAMS_PASS]
        self._imap_max_messages_count = int(imap_config[PARAMS_IMAP_MAX_MESSAGES])

        # Read smtp configuration
        smtp_config = config["SMTP"]
        self._smtp_server = smtp_config[PARAMS_SERVER]
        self._imap_username = imap_config[PARAMS_USER]
        self._imap_password = imap_config[PARAMS_PASS]

    def register_action(self, subject: str, callback: Callable[['MailManager', str], None]) -> None:
        """
        Register a callback function to be called when a new email with given subject is received.
        The callback function will receive the email body as a string.
        """
        if subject in self._callbacks:
            raise Exception("Callback already registered for subject %s" % subject)
        self._callbacks[subject.lower()] = callback

    def register_default(self, callback: Callable[['MailManager', email.message.EmailMessage], None]) -> None:
        """
        Register a callback function to be called when a new email is received.
        The callback function will receive the email body as a string.
        """
        self._default_callback = callback

    def connect(self) -> None:
        """
        Connect to the IMAP server. Required before any call to read().
        """
        # create an IMAP4 class with SSL, use your email provider's IMAP server
        self._imap = imaplib.IMAP4_SSL(self._imap_server)
        # authenticate
        self._imap.login(self._imap_username, self._imap_password)

    def fetch(self) -> list[email.message.EmailMessage]:
        """
        Fetch emails from the IMAP server. 
        Execute any callback registered for the subject of the email.

        If no action is registered for the subject of the email, the email is ignored.
        """
        # Prepare result
        result = []
        # select a mailbox (in this case, the inbox mailbox)
        # use imap.list() to get the list of mailboxes
        retcode, messages = self._imap.select("INBOX", readonly=False) # Will mark mail as read
        if retcode != "OK":
            print("ERROR: Unable to open mailbox")
            return

        retcode, messages = self._imap.search(None, "(UNSEEN)")
        if retcode != "OK":
            print("ERROR: Unable to fetch unseen emails")
            return

        # List of unseen email ids
        mail_ids = messages[0].split()
        mail_ids.reverse()
        print(f"Will process {len(mail_ids)} email(s)")

        # Read emails
        for mail_id in mail_ids:
            # fetch the email body (RFC822) for the given ID
            status, data = self._imap.fetch(mail_id, "(RFC822)")
            if status != "OK":
                print("ERROR: Unable to fetch email")
                continue

            # parse email and extract image
            email_body = data[0][1]
            email_body = email.message_from_bytes(email_body)

            # get subject
            subject = email_body["Subject"]
            sender = email_body["From"]

            potential_action = subject.lower()
            if potential_action in self._callbacks:
                print(f"Executing callback for subject {subject}...")
                try:
                    content = quopri.decodestring(email_body.get_payload()).decode("utf-8")
                    self._callbacks[potential_action](self, content)
                except Exception as e:
                    # If action's callback fail, log error, but continue
                    print(f"Error while executing callback for action {potential_action}: {e}")
                    self.send(f"Error while executing callback for action {potential_action} from {sender}", str(e))
            elif self._default_callback is not None:
                try:
                    self._default_callback(self, email_body)
                except Exception as e:
                    # If default callback fail, log error, but continue
                    print(f"Error while executing default callback: {e}")
                    self.send(f"Error while executing default callback from {sender}", str(e))
            else:
                print("Email ignored %s from %s" % (subject, sender))

        return result

    def send(self, subject: str, body: str) -> None:
        """
        Send an email to the SMTP server.
        """
        try:
            # create message
            msg = email.message.EmailMessage()
            msg["Subject"] = subject
            msg["From"] = self._imap_username
            msg["To"] = self._admin_email
            msg.set_content(body)

            # send the message
            smtp = smtplib.SMTP(self._smtp_server)
            smtp.ehlo()
            smtp.starttls()
            smtp.login(self._imap_username, self._imap_password)
            smtp.send_message(msg)
            smtp.quit()
        except Exception as e:
            print(f"Error while sending email: {e}")