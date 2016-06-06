""" This is the Bouncing Egg bot backend for a Telegram bot. """

# Imports
import telegram
import ts3.query
import time
import datetime
import os
import sqlite3
import json
import urllib.request
import urllib.error
import pymysql
import copy

# Global Variable Dictionaries for Configuration, Emoji, and Messages.
CONFIG = {"VERSION": "0.032; 29.12.2015"}
EMOJI = {}
MSGS = {}

# Sets whether or not the bot should archive to a remove MySQL database.
# Note: This requires the mysql fields set in the configuration file.
REMOTE_ARCHIVE = True


def main():
    """
        Bot startup routine, loads the configuration/emoji and enters the main loop.
    """
    load_cfg()
    init_emoji()
    init_msgs()

    bot = telegram.Bot(token=CONFIG["TOKEN"])
    bot_info = bot.getMe()
    CONFIG["BOTINFO"] = bot_info
    started = datetime.datetime.now()

    try:
        CONFIG["LAST_UPDATE_ID"] = bot.getUpdates()[-1].update_id + 1
    except IndexError:
        CONFIG["LAST_UPDATE_ID"] = None

    print("BEGBot connected: Name={}, ID={}, Started={}".format(bot_info.username,
                                                                bot_info.id, started))

    print("SessionID: {}".format(CONFIG["SESSION_ID"]))

    while True:
        loop(bot)  # this includes a few seconds timeout
        send_keep_alive(CONFIG["SESSION_ID"])


def loop(bot):
    """
        Main loop of the bot, collects updates from the Telegram API and performs actions on them.

        @param bot The telegram bot instance created by the telegram module.
    """
    global CONFIG

    # Management of the Birthday check. Reset from 0-1, check from 9-10.
    now = datetime.datetime.now()
    if now.hour == 0:
        CONFIG["TODAYS_BDAY_CHECK"] = False
    if now.hour == 9 and not CONFIG["TODAYS_BDAY_CHECK"]:
        bday_messages = check_for_birthdays()
        for bdm in bday_messages:
            bot.sendMessage(chat_id=CONFIG["BEG_ID"], text=bdm)
        CONFIG["TODAYS_BDAY_CHECK"] = True

    # Receiving and processing updates.
    try:
        for u in bot.getUpdates(offset=CONFIG["LAST_UPDATE_ID"], timeout=6):
            archive(u, bot)

            # UTF-8 Encoded message text
            message_text = u.message.text.encode('utf-8')
            sender = u.message.from_user.id

            if sender not in CONFIG["KNOWN_USERS"]:
                add_user(u.message.from_user)

            # print("Received Message from {}: {}".format(sender, message_text))

            # Public string matching
            response = match_text(message_text)
            if response is not None:
                bot.sendMessage(chat_id=u.message.chat_id, text=response)

            # BEG only commands
            # Maybe check if u.message.chat.type == "private" or "group", if necessary.
            if u.message.text == "/ts3" or u.message.text == "/ts3{}".format(CONFIG["BOTINFO"].name):
                if is_beg(sender):
                    ts3status = get_ts3_status()
                    bot.sendMessage(chat_id=u.message.chat_id, text=ts3status)
                else:
                    bot.sendMessage(chat_id=u.message.chat_id,
                                    text=MSGS["ONLY_FOR_BEG"])

            if u.message.text == "/steam" or u.message.text == "/steam{}".format(CONFIG["BOTINFO"].name):
                if is_beg(sender):
                    steamstats = get_steam_status()
                    bot.sendMessage(chat_id=u.message.chat_id, text=steamstats)
                else:
                    bot.sendMessage(chat_id=u.message.chat_id,
                                    text=MSGS["ONLY_FOR_BEG"])

            if u.message.text == "/version" or u.message.text == "/version{}".format(CONFIG["BOTINFO"].name):
                if is_beg(sender):
                    bot.sendMessage(chat_id=u.message.chat_id,
                                    text="BEGBot - Current Version: {}".format(CONFIG["VERSION"]))
                else:
                    bot.sendMessage(chat_id=u.message.chat_id,
                                    text=MSGS["ONLY_FOR_BEG"])

            # Admin only commands
            if u.message.text == "/session" or u.message.text == "/session{}".format(CONFIG["BOTINFO"].name):
                if is_admin(sender):
                    (s_id, s_start, s_end, s_duration) = get_session(CONFIG["SESSION_ID"])
                    bot.sendMessage(chat_id=u.message.chat_id,
                                    text="Session: id={}, start={}, lastka={}, duration={}s"
                                    .format(s_id, s_start, s_end, s_duration))
                else:
                    bot.sendMessage(chat_id=u.message.chat_id, text=MSGS["ONLY_FOR_ADMINS"])

            if u.message.text == "/listusers" or u.message.text == "/listusers{}".format(CONFIG["BOTINFO"].name):
                if is_admin(sender):
                    users = "\n".join([str(u) for u in get_all_users()])
                    bot.sendMessage(chat_id=u.message.chat_id, text="Users:\n{}".format(users))
                else:
                    bot.sendMessage(chat_id=u.message.chat_id, text=MSGS["ONLY_FOR_ADMINS"])

            if u.message.text == "/listnonbeg" or u.message.text == "/listnonbeg{}".format(CONFIG["BOTINFO"].name):
                if is_admin(sender):
                    nonbeg = "\n".join([str(u) for u in get_non_beg_users()])
                    bot.sendMessage(chat_id=u.message.chat_id,
                                    text="Non-BEG Users:\n{}".format(nonbeg))
                else:
                    bot.sendMessage(chat_id=u.message.chat_id, text=MSGS["ONLY_FOR_ADMINS"])

            if u.message.text.startswith("/setbday ") or u.message.text.startswith("/setbday{} ".format(CONFIG["BOTINFO"].name)):
                if is_admin(sender):
                    params = message_text[9:].split()
                    if len(params) != 2:
                        bot.sendMessage(chat_id=u.message.chat_id,
                                        text="{} Error. Wrong parameter count."
                                        .format(EMOJI["BANG"]))
                    else:
                        try:
                            uid = int(params[0])
                            bday = params[1].decode("utf-8")
                            if len(bday) != 10:
                                bot.sendMessage(chat_id=u.message.chat_id,
                                                text="{} Error. Malformed date, expected format:"
                                                     " \"YYYY-MM-DD\"."
                                                .format(EMOJI["BANG"]))
                            else:
                                result = set_bday(uid, bday)
                                if result is None:
                                    bot.sendMessage(chat_id=u.message.chat_id,
                                                    text="{} Error. Unknown user ID."
                                                    .format(EMOJI["BANG"]))
                                else:
                                    (uname, _, tid) = result
                                    bot.sendMessage(chat_id=u.message.chat_id,
                                                    text="Successfully set birthday for"
                                                         " {} ({}) to {}."
                                                    .format(uname, tid, bday))
                        except ValueError:
                            bot.sendMessage(chat_id=u.message.chat_id,
                                            text="{} Error. Malformed user ID."
                                            .format(EMOJI["BANG"]))

            if u.message.text.startswith("/addbeg ") or u.message.text.startswith("/addbeg{} ".format(CONFIG["BOTINFO"].name)):
                if is_admin(sender):
                    try:
                        uid = int(message_text[8:])
                        uinfo = get_user_by_id(uid)
                        if uinfo is None:
                            bot.sendMessage(chat_id=u.message.chat_id,
                                            text="{} Error. Unknown user ID."
                                            .format(EMOJI["BANG"]))
                        else:
                            add_user_to_beg(uid)
                            bot.sendMessage(chat_id=u.message.chat_id,
                                            text="{} Successfully added: {} ({}) {} Welcome! {}"
                                            .format(EMOJI["PARTY_BALL"], uinfo[1], uinfo[3],
                                                    EMOJI["SPARKLE"], EMOJI["PARTY_CONE"]))
                    except ValueError:
                        bot.sendMessage(chat_id=u.message.chat_id,
                                        text="{} Error. Malformed user ID."
                                        .format(EMOJI["BANG"]))
                else:
                    bot.sendMessage(chat_id=u.message.chat_id, text=MSGS["ONLY_FOR_ADMINS"])

            CONFIG["LAST_UPDATE_ID"] = u.update_id + 1
    except telegram.TelegramError as err:
        print("{}  Telegram Error, sleeping {}s and trying again: {}"
              .format(datetime.datetime.now(), CONFIG["ERROR_TIMEOUT"], err))
        time.sleep(CONFIG["ERROR_TIMEOUT"])
    except ValueError as err:
        print("{}  Value Error, sleeping {}s and trying again: {}"
              .format(datetime.datetime.now(), CONFIG["ERROR_TIMEOUT"], err))
        time.sleep(CONFIG["ERROR_TIMEOUT"])
    except urllib.error.URLError as err:
        print("{}  URL Error, sleeping {}s and trying again: {}"
              .format(datetime.datetime.now(), CONFIG["ERROR_TIMEOUT"], err))
        time.sleep(CONFIG["ERROR_TIMEOUT"])


def archive(update, bot):
    """
    Archives/persists the received update into the database.

    @param update: The update as defined by the telegram module.
    @param bot: The Telegram bot instance.
    """
    if update.message is None:
        print("Error: message is None ... Update is:")
        print(update)
    else:
        if update.message.chat.type == "group":
            # Persist into local SQLite3 database.
            user = update.message.from_user
            con = sqlite3.connect(CONFIG["DB_FILE"])
            c = con.cursor()
            c.execute("insert into message (session_id, telegram_id, message_id, update_id, group_id,"
                      " content, received) values (?, ?, ?, ?, ?, ?, datetime('now'))",
                      (CONFIG["SESSION_ID"], user.id, update.message.message_id, update.update_id,
                       update.message.chat.id, str(update)))
            con.commit()
            c.close()
            con.close()

            # Persist into remote MySQL database, if enabled.
            if REMOTE_ARCHIVE:
                mysql_con = pymysql.connect(host=CONFIG["MYSQL_SRV"], user=CONFIG["MYSQL_USR"],
                                            password=CONFIG["MYSQL_PWD"], db=CONFIG["MYSQL_DB"],
                                            charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor)
                try:
                    with mysql_con.cursor() as mysql_c:
                        # Copy update object and encode message text to UTF-8
                        update_copy = copy.deepcopy(update)
                        update_copy.message.text = update.message.text.encode("utf-8")
                        mysql_c.execute("insert into message (session_id, telegram_id, message_id, update_id, group_id,"
                                        " content, received) values (%s, %s, %s, %s, %s, %s, NOW());",
                                        (CONFIG["SESSION_ID"], user.id, update.message.message_id, update.update_id,
                                         update.message.chat.id, str(update_copy)))
                finally:
                    mysql_con.close()

            if update.message.sticker is not None:
                download_file(update.message.sticker.file_id, bot, ftype="sticker")
                download_file(update.message.sticker.thumb.file_id, bot, ftype="sticker_thumb")
            elif update.message.document is not None:
                download_file(update.message.document.file_id, bot, ftype=str(update.message.document.mime_type))
                if update.message.document.thumb is not None:
                    download_file(update.message.document.thumb.file_id, bot, ftype="document_thumb")
            elif update.message.voice is not None:
                download_file(update.message.voice.file_id, bot, ftype=str(update.message.voice.mime_type))
            elif update.message.video is not None:
                download_file(update.message.video.file_id, bot, ftype="video")
                download_file(update.message.video.thumb.file_id, bot, ftype="video_thumb")
            elif update.message.photo is not None:
                for i, p in enumerate(update.message.photo):
                    download_file(p.file_id, bot, ftype="photo_s{}".format(i))


def download_file(file_id, bot, ftype=None):
    """
    Downloads a file from Telegram and stores it to the file system
    and a description into the remote MySQL database, if enabled.

    @param file_id: File ID of the file do be downloaded
    @param bot: The telegram bot instance.
    @param ftype: File type description.
    @return: The file path of the downloaded file.
    """
    file_path = "{}/{}".format(CONFIG["FILES_DIR"], file_id)

    if not os.path.isfile(file_path):
        file = bot.getFile(file_id=file_id)
        file.download(custom_path=str(file_id))
        os.rename(str(file_id), file_path)

        if REMOTE_ARCHIVE:
            mysql_con = pymysql.connect(host=CONFIG["MYSQL_SRV"], user=CONFIG["MYSQL_USR"],
                                        password=CONFIG["MYSQL_PWD"], db=CONFIG["MYSQL_DB"],
                                        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor)
            try:
                with mysql_con.cursor() as mysql_c:
                    mysql_c.execute("insert into file (file_id, type, received) values (%s, %s, NOW());",
                                    (str(file_id), ftype))
            finally:
                mysql_con.close()

    return file_path


def match_text(text):
    """
        Matches the given text to several patterns and returns a string if a bot reply is
        warranted, or None if not.

        @param text The text that we try to match the patterns to.
    """

    # Matches an Imgur direct link.
    text = text.decode("utf-8")
    if text.startswith("http://i.imgur.com/") and not text.endswith(".gifv"):
        site = urllib.request.urlopen(text)
        if site.getheader("Content-Type") == "image/gif":
            # GIF not linked as GIFV
            sitesize = int(site.getheader("Content-Length")) / 1024 / 1024
            newsite = "{}.gifv".format(text[:-4])
            return "{} Warning: Non-GIFV GIF detected! You don't want to download" \
                   " {:.2f}MB, do you? Here's the proper link: {} {}" \
                .format(EMOJI["WARNING"], sitesize, EMOJI["EARTH_AFRICA_EUROPE"], newsite)

    # If nothing has been matched until this point, just return None.
    return None


def send_keep_alive(session_id):
    """
        Saves the current time to the database to keep track of the last known working time in
        case the bot crashed.

        @param session_id The ID of the current bot session.
    """
    con = sqlite3.connect(CONFIG["DB_FILE"])
    con.execute("update session set end = datetime('now') where id=?", (session_id,))
    con.commit()
    con.close()


def get_session(session_id):
    """
        Gets information (start time, end time, and duration about the current session
        by session_id.

        @param session_id The ID of the current bot session.
    """
    con = sqlite3.connect(CONFIG["DB_FILE"])
    c = con.cursor()
    c.execute("select id, start, end, strftime('%s', end) - strftime('%s', start) as duration "
              "from session where id=?",
              (session_id,))
    result = c.fetchone()
    c.close()
    con.close()
    return result


def set_bday(user_id, bday):
    """
        Adds the given birth date for the given user to the database.

        @param user_id The user id as it is in the database.
        @param bday The birth date as a string in the format "YYYY-MM-DD".
        @return Returns a tuple of (user name, first name, telegram id) for the given user id.
    """
    con = sqlite3.connect(CONFIG["DB_FILE"])
    c = con.cursor()
    c.execute("update user set bday = ? where id = ?", (bday, user_id))
    con.commit()
    c.execute("select username, firstname, telegram_id from user where id = ?", (user_id,))
    result = c.fetchone()
    c.close()
    con.close()
    return result


def add_user(user):
    """
        Adds the given user to the database and the KNOWN_USERS dictionary.

        @param user The user as defined by the telegram module.
    """
    global CONFIG
    con = sqlite3.connect(CONFIG["DB_FILE"])
    c = con.cursor()
    c.execute("insert into user (username, firstname, lastname, telegram_id, added, beg, admin)"
              " values (?, ?, ?, ?, datetime('now'), 0, 0)",
              (user.username, user.first_name, user.last_name, user.id))
    con.commit()
    c.close()
    con.close()
    CONFIG["KNOWN_USERS"].add(user.id)


def get_user_by_id(user_id):
    """
        Returns information (username, first name, last name, telegram id)) about a user
        identified by his user_id (not telegram id!).

        @param user_id The user id as it is in the database.
    """
    con = sqlite3.connect(CONFIG["DB_FILE"])
    c = con.cursor()
    c.execute("select username, firstname, lastname, telegram_id from user where id=?",
              (user_id,))
    result = c.fetchone()
    c.close()
    con.close()
    return result


def get_all_users():
    """
        Returns a list of all users in the database.
    """
    con = sqlite3.connect(CONFIG["DB_FILE"])
    c = con.cursor()
    c.execute("select * from user")
    result = c.fetchall()
    c.close()
    con.close()
    return result


def get_non_beg_users():
    """
        Returns a list of all users in the database that are not tagged as BEG members.
    """
    con = sqlite3.connect(CONFIG["DB_FILE"])
    c = con.cursor()
    c.execute("select id, username, firstname, lastname, telegram_id from user where beg != 1")
    result = c.fetchall()
    c.close()
    con.close()
    return result


def add_user_to_beg(user_id):
    """
        Tags the user with the given user_id as a BEG member.

        @param user_id The user id as it is in the database.
    """
    con = sqlite3.connect(CONFIG["DB_FILE"])
    con.execute("update user set beg = 1 where id=?", (user_id,))
    con.commit()
    con.close()


def is_admin(telegram_id):
    """
        Checks if the user with the given telegram id has administrator permissions.

        @param telegram_id The users telegram id.
    """
    con = sqlite3.connect(CONFIG["DB_FILE"])
    c = con.cursor()
    c.execute("select count(id) from user where admin=1 and telegram_id=?", (telegram_id,))
    (result,) = c.fetchone()
    c.close()
    con.close()
    return result


def is_beg(telegram_id):
    """
        Checks if the user with the given telegram id is tagged as a BEG member.

        @param telegram_id The users telegram id.
    """
    con = sqlite3.connect(CONFIG["DB_FILE"])
    c = con.cursor()
    c.execute("select count(id) from user where beg=1 and telegram_id=?", (telegram_id,))
    (result,) = c.fetchone()
    c.close()
    con.close()
    return result


def check_for_birthdays():
    """
        Checks if one or more of the bouncing egg members have a birthday today and returns a
        list of strings corresponding to birthday wishes for each user with a birthday today.
    """
    con = sqlite3.connect(CONFIG["DB_FILE"])
    c = con.cursor()
    c.execute("select id, firstname, bday from user where beg = 1")
    result = c.fetchall()
    c.close()
    con.close()
    msgs = []
    for r in result:
        if r[2] is not None:
            bday = r[2].split("-")
            if len(bday) == 3:
                try:
                    for i, bde in enumerate(bday):
                        bday[i] = int(bde)
                    today = datetime.datetime.now()
                    today = (today.month, today.day)
                    bday = (bday[1], bday[2])
                    if today == bday:
                        msg = "{}  {}  {}  Happy Birthday, {}!  {}  {}  {}" \
                            .format(EMOJI["PARTY_CONE"], EMOJI["SPARKLE"],
                                    EMOJI["BALLOON"], r[1], EMOJI["BALLOON"],
                                    EMOJI["CAKE"], EMOJI["PRESENT"])
                        msgs.append(msg)
                except ValueError:
                    print("Encountered malformed birthday for user id {}, "
                          "please check and correct.".format(r[0]))
    return msgs


def get_steam_status():
    """
        Connects to the Steam Web API as defined in the cfguration file and returns a string
        resembling the currently online users in steam, or None if the request failed.
    """
    states = {
        0: "Offline",
        1: "Online",
        2: "Busy",
        3: "Away",
        4: "Snooze",
        5: "Looking to Trade",
        6: "Looking to Play"
    }

    site = urllib.request.urlopen("http://api.steampowered.com/ISteamUser/"
                                  "GetPlayerSummaries/v0002/?key={}&steamids={}"
                                  .format(CONFIG["STEAM_API_KEY"], ",".join(CONFIG["STEAM_IDS"])))
    content = site.read()
    try:
        data = json.loads(content.decode("utf-8"))
        pinfo = []
        for p in data["response"]["players"]:
            if p["personastate"] != 0:
                pstate = states[p["personastate"]]
                if "gameid" in p:
                    pstate = "{} / InGame".format(pstate)
                pinfo.append("{} {} {}".format(p["personaname"], EMOJI["SQUIGGLY_LINE"], pstate))
        if len(pinfo) > 0:
            return "{}{} Steam {}{}\n{} {}" \
                .format(EMOJI["THICK_DASH"], EMOJI["THICK_DASH"], EMOJI["THICK_DASH"], EMOJI["THICK_DASH"],
                        EMOJI["ORANGE_RHOMBUS"], "\n{} ".format(EMOJI["ORANGE_RHOMBUS"]).join(pinfo))
        else:
            return "{}{} Steam {}{}\nThere's nobody online {}" \
                .format(EMOJI["THICK_DASH"], EMOJI["THICK_DASH"], EMOJI["THICK_DASH"],
                        EMOJI["THICK_DASH"], EMOJI["SAD"])

    except ValueError:
        print("Error: Steam API sent empty response.")

    return "{}{} Steam {}{}\nThe Steam API sent nothing {}" \
        .format(EMOJI["THICK_DASH"], EMOJI["THICK_DASH"], EMOJI["THICK_DASH"], EMOJI["THICK_DASH"], EMOJI["SAD"])


def get_ts3_status():
    """
        Connects to the TeamSpeak 3 server as defined in the configuration file and returns
        a string resembling the currently online users.
    """
    try:
        ts3con = ts3.query.TS3Connection(CONFIG["TS3_SRV"])
    except ConnectionRefusedError as err:
        print("TS3 connection failed: {}".format(err))
        return "{} TS3 Error {}".format(EMOJI["BANG"], EMOJI["BANG"])

    channels = {}
    clients = []

    try:
        ts3con.login(client_login_name=CONFIG["TS3_USR"], client_login_password=CONFIG["TS3_PWD"])
        ts3con.use(sid=1)

        resp = ts3con.clientlist()
        for client in resp.parsed:
            if not client["client_nickname"].startswith("{} from ".format(CONFIG["TS3_USR"])):
                channels[client["cid"]] = 0
                clients.append((client["client_nickname"], client["cid"]))

        if len(clients) == 0:
            return "{}{} TeamSpeak 3 {}{}\n There's nobody online {}" \
                .format(EMOJI["THICK_DASH"], EMOJI["THICK_DASH"], EMOJI["THICK_DASH"],
                        EMOJI["THICK_DASH"], EMOJI["SAD"])

        resp = ts3con.channellist()
        for channel in resp.parsed:
            if channel["cid"] in channels:
                channels[channel["cid"]] = {"name": channel["channel_name"], "clients": []}

        for (cname, cid) in clients:
            channels[cid]["clients"].append(cname)

        entries = []
        for c in channels:
            clientlines = []
            for client in range(0, len(channels[c]["clients"])):
                if client == len(channels[c]["clients"]) - 1:
                    clientlines.append(" {} {} {}".format(EMOJI["CROSSING_L"], EMOJI["BLUE_BALL"],
                                                          channels[c]["clients"][client]))
                else:
                    clientlines.append(" {} {} {}".format(EMOJI["CROSSING_T"], EMOJI["BLUE_BALL"],
                                                          channels[c]["clients"][client]))

            entries.append("{} {}\n{}".format(EMOJI["SPEECH_BUBBLE"], channels[c]["name"],
                                              "\n".join(clientlines)))

        return "{}{} TeamSpeak 3 {}{}\n{}" \
            .format(EMOJI["THICK_DASH"], EMOJI["THICK_DASH"], EMOJI["THICK_DASH"],
                    EMOJI["THICK_DASH"], "\n".join(entries))

    except ts3.query.TS3QueryError as err:
        print("TS3 query failed:", err.resp.error["msg"])
        return "{} TS3 Error {}".format(EMOJI["BANG"], EMOJI["BANG"])


def load_cfg():
    """
        Loads bot settings and cfguration from the file cfg.json.
    """
    global CONFIG

    # Default cfg values
    CONFIG["ERROR_TIMEOUT"] = 3
    CONFIG["LAST_UPDATE_ID"] = 0
    CONFIG["SESSION_ID"] = -1
    CONFIG["KNOWN_USERS"] = {}
    CONFIG["DB_FILE"] = ""
    CONFIG["ADMIN_ID"] = 1
    CONFIG["BEG_ID"] = -1
    CONFIG["TOKEN"] = ""
    CONFIG["TS3_USR"] = ""
    CONFIG["TS3_PWD"] = ""
    CONFIG["TS3_SRV"] = ""
    CONFIG["STEAM_API_KEY"] = ""
    CONFIG["STEAM_IDS"] = []
    CONFIG["TODAYS_BDAY_CHECK"] = False

    # Read configuration values from file.
    with open("config.json", "r") as f:
        cfg = json.load(f)

    try:
        # Get local SQLite3 database config entries.
        schema_script = cfg["db_schema"]
        CONFIG["DB_FILE"] = cfg["db_file"]

        # Get telegram config entries.
        CONFIG["ADMIN_ID"] = cfg["admin_id"]
        CONFIG["BEG_ID"] = cfg["group_id"]
        CONFIG["TOKEN"] = cfg["token"]

        # Get file system config entries.
        CONFIG["FILES_DIR"] = cfg["files_dir"]

        # Get TeamSpeak3 config entries.
        CONFIG["TS3_USR"] = cfg["ts3_usr"]
        CONFIG["TS3_PWD"] = cfg["ts3_pwd"]
        CONFIG["TS3_SRV"] = cfg["ts3_srv"]

        # Get Steam config entries.
        CONFIG["STEAM_API_KEY"] = cfg["steam_api_key"]
        CONFIG["STEAM_IDS"] = [str(sid) for sid in cfg["steam_ids"]]

        # Connect to local SQLite3 DB (create first, if it does not exist)
        new_db = not os.path.exists(CONFIG["DB_FILE"])
        con = sqlite3.connect(CONFIG["DB_FILE"])
        if new_db:
            print("File '{}' not found. Creating new database.".format(CONFIG["DB_FILE"]))
            with open(schema_script, "rt") as f:
                schema = f.read()
            con.executescript(schema)
            c = con.cursor()
            c.execute("insert into user (username, firstname, telegram_id, added, beg, admin) values "
                      "('Admin', 'Admin', ?, datetime('now'), 1, 1)", (CONFIG["ADMIN_ID"],))
            con.commit()
            c.close()
        else:
            print("Using database '{}'.".format(CONFIG["DB_FILE"]))
        c = con.cursor()
        c.execute("insert into session (start, end) values (datetime('now'), datetime('now'));")
        CONFIG["SESSION_ID"] = c.lastrowid
        con.commit()
        c.execute("select telegram_id from user")
        CONFIG["KNOWN_USERS"] = {u for (u,) in c.fetchall()}
        c.close()
        con.close()

        # Get remote MySQL database config entries.
        if REMOTE_ARCHIVE:
            CONFIG["MYSQL_SRV"] = cfg["mysql_srv"]
            CONFIG["MYSQL_DB"] = cfg["mysql_db"]
            CONFIG["MYSQL_USR"] = cfg["mysql_usr"]
            CONFIG["MYSQL_PWD"] = cfg["mysql_pwd"]

    except KeyError as err:
        print("Error: Missing field in config.json: {}".format(err))
        exit()


def init_emoji():
    global EMOJI
    EMOJI["SAD"] = b"\xf0\x9f\x98\x9f"
    EMOJI["BLUE_RHOMBUS"] = b"\xf0\x9f\x94\xb9"
    EMOJI["BANG"] = b"\xf0\x9f\x92\xa2"
    EMOJI["PARTY_CONE"] = b"\xf0\x9f\x8e\x89"
    EMOJI["PARTY_BALL"] = b"\xf0\x9f\x8e\x8a"
    EMOJI["SPARKLE"] = b"\xe2\x9c\xa8"
    EMOJI["BLUE_BALL"] = b"\xf0\x9f\x94\xb5"
    EMOJI["RED_BALL"] = b"\xf0\x9f\x94\xb4"
    EMOJI["SPEECH_BUBBLE"] = b"\xf0\x9f\x92\xac"
    EMOJI["THICK_DASH"] = b"\xe2\x9e\x96"
    EMOJI["CROSSING_T"] = b"\xe2\x94\x9c"
    EMOJI["CROSSING_L"] = b"\xe2\x94\x94"
    EMOJI["WARNING"] = b"\xe2\x9a\xa0\xef\xb8\x8f"
    EMOJI["EARTH_AFRICA_EUROPE"] = b"\xf0\x9f\x8c\x8d"
    EMOJI["ORANGE_RHOMBUS"] = b"\xf0\x9f\x94\xb6"
    EMOJI["SQUIGGLY_LINE"] = b"\xe3\x80\xb0"
    EMOJI["CAKE"] = b"\xf0\x9f\x8e\x82"
    EMOJI["PRESENT"] = b"\xf0\x9f\x8e\x81"
    EMOJI["BALLOON"] = b"\xf0\x9f\x8e\x88"
    for e in EMOJI:
        EMOJI[e] = EMOJI[e].decode("utf-8")


def init_msgs():
    global MSGS
    MSGS["ONLY_FOR_ADMINS"] = "{} Sorry, only for bot administrators.".format(EMOJI["BANG"])
    MSGS["ONLY_FOR_BEG"] = "{} Sorry, only for Bouncing Egg members.".format(EMOJI["BANG"])


if __name__ == "__main__":
    main()
