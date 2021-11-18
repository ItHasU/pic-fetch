import configparser
import email
import getpass
import imaplib
import os
import uuid
from email.header import decode_header

SECTION_IMAP = "IMAP"
PARAMS_IMAP_SERVER = "Server"
PARAMS_IMAP_USER = "Username"
PARAMS_IMAP_PASS = "Password"
PARAMS_IMAP_MAX_MESSAGES = "MaxMessagesCount"

SECTION_PICTURES = "PICTURES"
PARAMS_PICTURES_FOLDER = "Cache"
PARAMS_PICTURES_MAX = "MaxPicturesCount"


def clean(text):
    # clean text for creating a folder
    return "".join(c if c.isalnum() else "_" for c in text)


###############################################################################
# Read configuration file #####################################################
config = configparser.ConfigParser()
config.read("config.ini")

# account credentials
server = config[SECTION_IMAP][PARAMS_IMAP_SERVER]
username = config[SECTION_IMAP][PARAMS_IMAP_USER]
password = config[SECTION_IMAP][PARAMS_IMAP_PASS]
max_messages_count = int(config[SECTION_IMAP][PARAMS_IMAP_MAX_MESSAGES])
pictures_folder = config[SECTION_PICTURES][PARAMS_PICTURES_FOLDER]
pictures_max_count = int(config[SECTION_PICTURES][PARAMS_PICTURES_MAX])

# Read emails #################################################################

# create an IMAP4 class with SSL, use your email provider's IMAP server
imap = imaplib.IMAP4_SSL(server)
# authenticate
imap.login(username, password)

# select a mailbox (in this case, the inbox mailbox)
# use imap.list() to get the list of mailboxes
status, messages = imap.select("INBOX")

# total number of emails
messages_count = int(messages[0])
read_count = min(messages_count, max_messages_count)

pictures = []

for i in range(read_count):
    if len(pictures) >= pictures_max_count:
        break

    print(
        "Reading message %d/%d (out of %d message(s))"
        % (i + 1, read_count, messages_count),
        end=None,
    )

    # fetch the email message by ID
    res, msg = imap.fetch(str(messages_count - i), "(RFC822)")
    for response in msg:
        if len(pictures) >= pictures_max_count:
            break
        if not isinstance(response, tuple):
            continue

        # parse a bytes email into a message object
        msg = email.message_from_bytes(response[1])

        # if the email message is multipart
        if not msg.is_multipart():
            continue

        # decode the email subject
        id, encoding = decode_header(msg["Message-Id"])[0]
        if isinstance(id, bytes):
            # if it's a bytes, decode to str
            id = id.decode(encoding)

        # iterate over email parts
        part_index = 0
        for part in msg.walk():
            if len(pictures) >= pictures_max_count:
                break
            # extract content type of email
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            try:
                # get the email body
                body = part.get_payload(decode=True).decode()
            except:
                pass

            filename = part.get_filename()
            if filename is not None and (
                filename.endswith(".jpg") or filename.endswith(".jpeg")
            ):
                filename = os.path.join(
                    pictures_folder, clean(id) + str(part_index) + ".jpg"
                )
                pictures.append(filename)  # Store picture to keep it
                part_index += 1
                open(filename, "wb").write(part.get_payload(decode=True))

# close the connection and logout
imap.close()
imap.logout()


# Clean pictures
from os import listdir
from os.path import isfile, join

files_to_delete = [
    os.path.join(pictures_folder, f)
    for f in listdir(pictures_folder)
    if not f.startswith(".")
]

for f in pictures:
    files_to_delete.remove(f)

for f in files_to_delete:
    print("Delete %s" % f)
    try:
        os.remove(f)
    except:
        pass
