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

def error_cb(mm: MailManager, body: str) -> None:
    print("ERROR: " + body)
    mm.send("Error message", body)

###############################################################################
# Read configuration file #####################################################
config = configparser.ConfigParser()
config.read("config.ini")

# account credentials
# pictures_folder = config[SECTION_PICTURES][PARAMS_PICTURES_FOLDER]
# pictures_max_count = int(config[SECTION_PICTURES][PARAMS_PICTURES_MAX])

reader = MailManager(config)
reader.register_action("error", error_cb)

reader.connect()
reader.process_unread()
