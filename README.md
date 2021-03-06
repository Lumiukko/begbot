# Bouncing Egg Telegram Bot

## Introduction

This is a bot-backend for the messenger Telegram. It allows users to run simple commands by sending them in Telegram to a dedicated chat group or the bot itself, and receive messages generated by this program. A function already implemented is the `/ts3` command, which queries a specified TeamSpeak3 server and responds with a list of members online.

For an introduction for bot creation and usage see: https://core.telegram.org/bots

## Python Packages required:

This bot was implemented using Python >= 3.4. Besides several standard libraries, the following packages are required:

* `python-telegram-bot` - https://github.com/leandrotoledo/python-telegram-bot/
* `ts3` - https://github.com/benediktschmitt/py-ts3
* `pymysql` - https://github.com/PyMySQL/PyMySQL

## Features

* On the command `/ts3` the bot will answer with an overview of people on the linked Teamspeak 3 server.
* On the commant `/steam` the bot will answer with an overview of people online in Steam (out of all Steam IDs defined in the configuration file).
* Admins can use the `/listusers` command to get a basic dump of all rows in the user database table.
* Admins can use the `/listnonbeg` command to get a basic dump of all rows with the beg flag not set in the user database table
* Admins can use the `/setbday <UID> <BDAY>` command to set the birth data of a user, where `<UID>` is the corresponding user id in the database and `<BDAY>` is the birth date of that user in the format `YYYY-MM-DD`.
* The bot checks every day at 9:00 if any of the users with the set beg flag has birthday and posts birthday wishes to the chat accordingly.
* If someone links a GIF from Imgur, which does not have the .gifv ending (i.e. WEBM converted GIF for saving bandwidth), the bot will post the corresponding GIFV link and mention how large the GIF file would have been to download in megabytes.
* The bot archives every update in JSON format into the database and downloads files (stickers, pictures, videos, documents, voice files) into a pre-defined folder a for future features, e.g. an archive function.
* Optionally the bot archives the messages into a remote MySQL database.

## Configuration

The configuration settings are read in from a file named `config.json` which has to be in the same folder as the program.

Here is an example of the `config.json` file:

```
{
  "token": "token for the telegram bot",
  "admin_id": telegram id of the first administrator,
  "group_id": telegram id of the group chat,
  "db_file": "path to the sqlite database file (will be generated if missing)",
  "db_schema": "path to the schema sql command (is used to create the database, if it doesn't exist)",
  "ts3_usr": "teamspeak 3 administrator username",
  "ts3_pwd": "teamspeak 3 administrator password",
  "ts3_srv": "teamspeak 3 server address",
  "steam_api_key": "steam web api key",
  "steam_ids": [
    first person steam id,
    second person steam id,
    ...
  ],
  "mysql_srv": "mysql host",
  "mysql_usr": "mysql user name",
  "mysql_pwd": "mysql password",
  "mysql_db": "mysql database name",
  "files_dir": "folder for file download"
}
```
