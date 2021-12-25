import configparser
import email
from email.header import decode_header

from api import MailManager

SECTION_IMAP = "IMAP"
SECTION_SMTP = "SMTP"
SECTION_PICTURES = "PICTURES"


def clean(text):
    # clean text for creating a folder
    return "".join(c if c.isalnum() else "_" for c in text)

###############################################################################
# Actions - Whitelist
###############################################################################

def whitelist_add_cb(mm: MailManager, message: email.message.EmailMessage) -> None:
    email = message["From"]
    if not mm.is_admin(email):
        mm.reply(message, "You are not allowed to do that")
        raise Exception("Not allowed")

    email_to_add = mm.get_email_content(message).split()[0]
    mm.whitelist_add(email_to_add)
    mm.reply(message, f"{email_to_add} added to whitelist")
    mm.send()

def whitelist_rm_cb(mm: MailManager, message: email.message.EmailMessage) -> None:
    print("Whitelist remove")
    email = message["From"]
    mm.whitelist_remove(email)
    mm.reply(message, f"{email} removed from whitelist")

def ping_cb(mm: MailManager, message: email.message.EmailMessage) -> None:
    print("PING from: " + message["From"])
    mm.send_admin("Notification", f"Received a ping from {message['From']}")
    mm.reply(message, f"Pong")

def default_cb(mm: MailManager, message: email.message.EmailMessage) -> None:
    if not mm.whitelist_has(message["From"]):
        # not in whitelist, ignore mail, but do not fail
        # we don't want to reply to the sender or spam the admin
        print(f"Ignoring mail from {message['From']}")
        return
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
reader.register_action("whitelist_add", whitelist_add_cb)
reader.register_action("ping", ping_cb)
reader.register_default(default_cb)

reader.connect()
reader.process_unread()
