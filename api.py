import configparser
import email
from email import message
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

    def register_action(self, subject: str, callback: Callable[['MailManager', email.message.EmailMessage], None]) -> None:
        """
        Register a callback function to be called when a new email with given subject is received.
        The callback function will receive the email body.
        """
        if subject in self._callbacks:
            raise Exception("Callback already registered for subject %s" % subject)
        self._callbacks[subject.lower()] = callback

    def register_default(self, callback: Callable[['MailManager', email.message.EmailMessage], None]) -> None:
        """
        Register a callback function to be called when a new email is received.
        The callback function will receive the email body.
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

    def process_unread(self) -> None:
        """
        Fetch unread emails from the IMAP server. 
        Execute any callback registered for the subject of the email.
        If the subject does not match any callback, execute the default callback.

        If the mail is well processed, it is marked as read.
        """
        # select a mailbox (in this case, the inbox mailbox)
        # use imap.list() to get the list of mailboxes
        retcode, messages = self._imap.select("INBOX", readonly=True) # Will not mark mail as read
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
        mail_to_mark_as_read = []
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

            try:
                if potential_action in self._callbacks:
                    print(f"Executing callback for subject {subject}...")
                    self._callbacks[potential_action](self, email_body)
                elif self._default_callback is not None:
                    self._default_callback(self, email_body)
                else:
                    print("Email ignored %s from %s" % (subject, sender))
                    continue
            except Exception as e:
                # If callback failed, log error, then continue
                print(f"Error while executing callback for action {potential_action}: {e}")
                self.send_admin(f"Error while executing callback for action {potential_action} from {sender}", str(e))
                continue

            # Callback was successfull, mark email as read
            mail_to_mark_as_read.append(mail_id)

        # Mark emails as read
        retcode, messages = self._imap.select("INBOX", readonly=False)
        for mail_id in mail_to_mark_as_read:
            self._imap.store(mail_id, '+FLAGS', '\Seen')

    def get_email_content(self, email_body: email.message.EmailMessage) -> str:
        return quopri.decodestring(email_body.get_payload()).decode("utf-8")

    def send_admin(self, subject: str, body: str) -> None:
        """
        Send an email to the admin.
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

    def reply(self, email_body: email.message.EmailMessage, content: str) -> None:
        """
        Send an email as a reply to the sender of the given email.
        """
        try:
            message_id = email_body["Message-Id"]

            # create message
            msg = email.message.EmailMessage()
            msg["Subject"] = "Re: " + email_body["Subject"]
            msg["From"] = self._imap_username
            msg["To"] = email_body["From"]
            if message_id is not None:
                msg["In-Reply-To"] = message_id
                msg["References"] = message_id
            msg.set_content(content)

            # send the message
            smtp = smtplib.SMTP(self._smtp_server)
            smtp.ehlo()
            smtp.starttls()
            smtp.login(self._imap_username, self._imap_password)
            smtp.send_message(msg)
            smtp.quit()
        except Exception as e:
            print(f"Error while sending email: {e}")