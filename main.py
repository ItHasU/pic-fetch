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
    if not mm.is_sender_admin(message):
        raise Exception(f"Not allowed: Whitelist add from {message['From']}")

    content = mm.get_email_content(message)
    email_to_add = content.split(" ")[0].strip()
    print(f"Adding {email_to_add} to whitelist...")
    mm.whitelist_add(email_to_add)
    mm.reply(message, f"{email_to_add} added to whitelist")
    mm.send(email_to_add, "You have been added to the whitelist", f"You can now send pictures to {mm._imap_username}")

def whitelist_rm_cb(mm: MailManager, message: email.message.EmailMessage) -> None:
    if not mm.is_sender_admin(message):
        raise Exception(f"Not allowed: Whitelist remove from {message['From']}")

    content = mm.get_email_content(message)
    email_to_remove = content.split(" ")[0].strip()
    print(f"Removing {email_to_remove} from whitelist...")
    mm.whitelist_remove(email_to_remove)
    mm.reply(message, f"{email_to_remove} removed from whitelist")
    mm.send(email_to_remove, "You have been removed from the whitelist", f"You can no longer send pictures to {mm._imap_username}")

def ping_cb(mm: MailManager, message: email.message.EmailMessage) -> None:
    sender = email['From']
    if not mm.whitelist_has(sender):
        # not in whitelist, ignore mail, but do not fail
        # we don't want to reply to the sender or spam the admin
        print(f"Ignoring mail from {message['From']}")
        return

    print("PING from: " + sender)
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
reader.register_action("whitelist_remove", whitelist_add_cb)
reader.register_action("ping", ping_cb)
reader.register_default(default_cb)

reader.connect()
reader.process_unread()
