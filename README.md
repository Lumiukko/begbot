# Bouncing Egg Telegram Bot

## Introduction

This is a bot-backend for the messenger Telegram. It allows users to run simple commands by sending them in Telegram to a dedicated chat group or the bot itself, and receive messages generated by this program. A function already implemented is the `/ts3` command, which queries a specified TeamSpeak3 server and responds with a list of members online.

For an introduction for bot creation and usage see: https://core.telegram.org/bots

## Python Packages required:

This bot was implemented using Python >= 3.4. Besides several standard libraries, the following packages are required:

* `python-telegram-bot` - https://github.com/leandrotoledo/python-telegram-bot/
* `py-ts3` - https://github.com/benediktschmitt/py-ts3

## Features

* On the command `/ts3` the bot will answer with an overview of people on the linked Teamspeak 3 server.
* If someone links a GIF from Imgur, which does not have the .gifv ending (i.e. WEBM converted GIF for saving bandwidth), the bot will post the corresponding GIFV link and mention how large the GIF file would have been to download in megabytes.

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
  "ts3_srv": "teamspeak 3 server address"
}
```
