import configparser
import email
import getpass
import imaplib
import os
import uuid
from email.header import decode_header

from api import MailManager

SECTION_IMAP = "IMAP"
SECTION_SMTP = "SMTP"
SECTION_PICTURES = "PICTURES"


def clean(text):
    # clean text for creating a folder
    return "".join(c if c.isalnum() else "_" for c in text)

###############################################################################
# Actions
###############################################################################

def ping_cb(mm: MailManager, message: email.message.EmailMessage) -> None:
    print("PING from: " + message["From"])
    mm.send_admin("Notification", f"Received a ping from {message['From']}")
    mm.reply(message, f"Pong")

def default_cb(mm: MailManager, message: email.message.EmailMessage) -> None:
    print("Default callback")
    mm.reply(message, "I don't know what to do with this message")

###############################################################################
# Read configuration file #####################################################
config = configparser.ConfigParser()
config.read("config.ini")

# account credentials
# pictures_folder = config[SECTION_PICTURES][PARAMS_PICTURES_FOLDER]
# pictures_max_count = int(config[SECTION_PICTURES][PARAMS_PICTURES_MAX])

reader = MailManager(config)
reader.register_action("ping", ping_cb)
reader.register_default(default_cb)

reader.connect()
reader.process_unread()
