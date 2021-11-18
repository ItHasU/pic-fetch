# pic-fetch
Fetch pictures from an inbox.

## Howto use

Create a file named `config.ini` in the project's folder, with the following format:
```
[IMAP]
Server=imap.gmail.com  # URL of the imap server
Username=xxx@gmail.com # Login for the imap server
Password=xxx           # 
MaxMessagesCount=20

[PICTURES]
Cache=cache
MaxPicturesCount=30
```

Run the program with the following command:
```
python main.py
```