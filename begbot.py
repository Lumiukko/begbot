# Imports
import telegram
import ts3.query
import time
import datetime
import os
import sqlite3
import json
import random
import urllib.request


# Global Variables
LAST_UPDATE_ID = 0
SESSION_ID = -1
KNOWN_USERS = {}
DB_FILE = ""
ADMIN_ID = 1
BEG_ID = -1
TOKEN = ""
TS3_USR = ""
TS3_PWD = ""
TS3_SRV = ""
STEAM_API_KEY = ""
STEAM_IDS = []
TODAYS_BDAY_CHECK = False


# Global variables for Emoji
emoji_sad = b"\xf0\x9f\x98\x9f".decode("utf-8")
emoji_blue_rhombus = b"\xf0\x9f\x94\xb9".decode("utf-8")
emoji_bang = b"\xf0\x9f\x92\xa2".decode("utf-8")
emoji_party_cone = b"\xf0\x9f\x8e\x89".decode("utf-8")
emoji_party_ball = b"\xf0\x9f\x8e\x8a".decode("utf-8")
emoji_sparkle = b"\xe2\x9c\xa8".decode("utf-8")
emoji_blue_ball = b"\xf0\x9f\x94\xb5".decode("utf-8")
emoji_red_ball = b"\xf0\x9f\x94\xb4".decode("utf-8")
emoji_speech_bubble = b"\xf0\x9f\x92\xac".decode("utf-8")
emoji_thick_dash = b"\xe2\x9e\x96".decode("utf-8")
emoji_crossing_t = b"\xe2\x94\x9c".decode("utf-8")
emoji_crossing_l = b"\xe2\x94\x94".decode("utf-8")
emoji_warning = b"\xe2\x9a\xa0\xef\xb8\x8f".decode("utf-8")
emoji_earth_africaeurope = b"\xf0\x9f\x8c\x8d".decode("utf-8")
emoji_orange_rhombus = b"\xf0\x9f\x94\xb6".decode("utf-8")
emoji_squiggly_line = b"\xe3\x80\xb0".decode("utf-8")
emoji_cake = b"\xf0\x9f\x8e\x82".decode("utf-8")
emoji_present = b"\xf0\x9f\x8e\x81".decode("utf-8")
emoji_balloon = b"\xf0\x9f\x8e\x88".decode("utf-8")

# Global variables for messages
msg_only_for_admins = "{} Sorry, only for bot administrators.".format(emoji_bang)


def main():
    """
        Bot startup routine, loads the configuration, and enters the main loop.
    """
    global LAST_UPDATE_ID
    global KNOWN_USERS

    load_config()

    bot = telegram.Bot(token=TOKEN)
    bot_info = bot.getMe()
    started = datetime.datetime.now()

    try:
        LAST_UPDATE_ID = bot.getUpdates()[-1].update_id + 1
    except IndexError:
        LAST_UPDATE_ID = None

    print("BEGBot connected: Name={}, ID={}, Started={}".format(bot_info.username, bot_info.id, started))

    print("SessionID: {}".format(SESSION_ID))

    while True:
        loop(bot)  # this includes a few seconds timeout
        send_keep_alive(SESSION_ID)


def loop(bot):
    """
        Main loop of the bot, collects updates from the Telegram API and performs actions on them.

        @param bot The telegram bot instance created by the telegram module.
    """
    global LAST_UPDATE_ID
    global TODAYS_BDAY_CHECK

    # Management of the Birthday check. Reset from 0-1, check from 9-10.
    now = datetime.datetime.now()
    if now.hour == 0:
        TODAYS_BDAY_CHECK = False
    if now.hour == 9 and not TODAYS_BDAY_CHECK:
        bday_messages = check_for_birthdays()
        for bdm in bday_messages:
            bot.sendMessage(chat_id=BEG_ID, text=bdm)
        TODAYS_BDAY_CHECK = True

    # Receiving and processing updates.
    try:
        for u in bot.getUpdates(offset=LAST_UPDATE_ID, timeout=6):
            archive(u)

            message_text = u.message.text.encode('utf-8')
            sender = u.message.from_user.id

            if sender not in KNOWN_USERS:
                add_user(u.message.from_user)

            # print("Received Message from {}: {}".format(sender, message_text))

            with open("mlog", "a", encoding="utf-8") as f:
                f.write(message_text.decode("utf-8"))
                f.write("\n")
            f.close()

            # Public string matching
            response = match_text(message_text)
            if response is not None:
                bot.sendMessage(chat_id=u.message.chat_id, text=response)

            # BEG only commands
            # Maybe check if u.message.chat.type == "private" or "group", if necessary.
            if message_text == b"/ts3":
                if is_beg(sender):
                    get_ts3_status()
                    ts3status = get_ts3_status()
                    bot.sendMessage(chat_id=u.message.chat_id, text=ts3status)
                else:
                    bot.sendMessage(chat_id=u.message.chat_id, text="{} Sorry, only for Bouncing Egg members."
                                    .format(emoji_bang))

            if message_text == b"/steam":
                if is_beg(sender):
                    get_ts3_status()
                    steamstats = get_steam_status()
                    bot.sendMessage(chat_id=u.message.chat_id, text=steamstats)
                else:
                    bot.sendMessage(chat_id=u.message.chat_id, text="{} Sorry, only for Bouncing Egg members."
                                    .format(emoji_bang))

            # Admin only commands
            if message_text == b"/session":
                if is_admin(sender):
                    (s_id, s_start, s_end, s_duration) = get_session(SESSION_ID)
                    bot.sendMessage(chat_id=u.message.chat_id, text="Session: id={}, start={}, lastka={}, duration={}s"
                                    .format(s_id, s_start, s_end, s_duration))
                else:
                    bot.sendMessage(chat_id=u.message.chat_id, text=msg_only_for_admins)

            if message_text == b"/listusers":
                if is_admin(sender):
                    users = "\n".join([str(u) for u in get_all_users()])
                    bot.sendMessage(chat_id=u.message.chat_id, text="Users:\n{}".format(users))
                else:
                    bot.sendMessage(chat_id=u.message.chat_id, text=msg_only_for_admins)

            if message_text == b"/listnonbeg":
                if is_admin(sender):
                    nonbeg = "\n".join([str(u) for u in get_non_beg_users()])
                    bot.sendMessage(chat_id=u.message.chat_id, text="Non-BEG Users:\n{}".format(nonbeg))
                else:
                    bot.sendMessage(chat_id=u.message.chat_id, text=msg_only_for_admins)

            if message_text.startswith(b"/setbday "):
                if is_admin(sender):
                    params = message_text[9:].split()
                    if len(params) != 2:
                        bot.sendMessage(chat_id=u.message.chat_id, text="{} Error. Wrong parameter count."
                                        .format(emoji_bang))
                    else:
                        try:
                            uid = int(params[0])
                            bday = params[1].decode("utf-8")
                            if len(bday) != 10:
                                bot.sendMessage(chat_id=u.message.chat_id,
                                                text="{} Error. Malformed date, expected format: \"YYYY-MM-DD\"."
                                                .format(emoji_bang))
                            else:
                                result = set_bday(uid, bday)
                                if result is None:
                                    bot.sendMessage(chat_id=u.message.chat_id, text="{} Error. Unknown user ID."
                                                    .format(emoji_bang))
                                else:
                                    (uname, fname, tid) = result
                                    bot.sendMessage(chat_id=u.message.chat_id,
                                                    text="Successfully set birthday for {} ({}) to {}."
                                                    .format(uname, tid, bday))
                        except ValueError:
                            bot.sendMessage(chat_id=u.message.chat_id, text="{} Error. Malformed user ID."
                                            .format(emoji_bang))

            if message_text.startswith(b"/addbeg "):
                if is_admin(sender):
                    try:
                        uid = int(message_text[8:])
                        uinfo = get_user_by_id(uid)
                        if uinfo is None:
                            bot.sendMessage(chat_id=u.message.chat_id, text="{} Error. Unknown user ID."
                                            .format(emoji_bang))
                        else:
                            add_user_to_beg(uid)
                            bot.sendMessage(chat_id=u.message.chat_id,
                                            text="{} Successfully added: {} ({}) {} Welcome! {}"
                                            .format(emoji_party_ball, uinfo[1], uinfo[3], emoji_sparkle,
                                                    emoji_party_cone))
                    except ValueError:
                        bot.sendMessage(chat_id=u.message.chat_id, text="{} Error. Malformed user ID."
                                        .format(emoji_bang))
                else:
                    bot.sendMessage(chat_id=u.message.chat_id, text=msg_only_for_admins)

            LAST_UPDATE_ID = u.update_id + 1
    except telegram.TelegramError as err:
        print("Telegram Error, sleeping 10s and trying again: {}".format(err))
        time.sleep(10)
    except ValueError as err:
        print("Value Error, sleeping 10s and trying again: {}".format(err))
        time.sleep(10)


def archive(update):
    """
        Archives/persists the received update into the database.

        @param update The update as defined by the telegram module.
    """
    if update.message.chat.type == "group" and update.message.chat.id == BEG_ID:
        user = update.message.from_user
        con = sqlite3.connect(DB_FILE)
        c = con.cursor()
        c.execute("insert into message (session_id, telegram_id, message_id, update_id, group_id, content, received)"
                  " values (?, ?, ?, ?, ?, ?, datetime('now'))",
                  (SESSION_ID, user.id, update.message.message_id, update.update_id,
                   update.message.chat.id, str(update)))
        con.commit()
        c.close()
        con.close()


def match_text(text):
    """
        Matches the given text to several patterns and returns a string if a bot reply is warranted, or None if not.

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
            return "{} Warning: Non-GIFV GIF detected! You don't want to download {:.2f}MB, do you?" \
                   " Here's the proper link: {} {}".format(emoji_warning, sitesize, emoji_earth_africaeurope, newsite)

    # That's what she said matching... simplex, change later into a more sophisticated matching...
    twss = b"\xef\xbb\xbf \xcd\xa1\xc2\xb0 \xcd\x9c\xca\x96 \xcd\xa1\xc2\xb0".decode("utf-8")
    twss = "That's what she said ({})".format(twss)
    wordbag = "zu aber riesig passt gross groß wow lang ui eng klein nie"
    wordbag = wordbag.split()
    textbag = text.split()
    hits = 0
    for w in wordbag:
        if w in textbag:
            hits += 1
    threshold = random.randint(3, 3+int(len(textbag)/2))
    if hits >= threshold:
        return twss

    # If nothing has been matched until this point, just return None.
    return None


def load_config():
    """
        Loads bot settings and configuration from the file config.json.
    """
    global KNOWN_USERS
    global SESSION_ID
    global DB_FILE
    global ADMIN_ID
    global BEG_ID
    global TOKEN
    global TS3_PWD
    global TS3_USR
    global TS3_SRV
    global STEAM_API_KEY
    global STEAM_IDS

    with open("config.json", "r") as f:
        config = json.load(f)

    schema_script = config["db_schema"]
    DB_FILE = config["db_file"]
    ADMIN_ID = config["admin_id"]
    BEG_ID = config["group_id"]
    TOKEN = config["token"]
    TS3_USR = config["ts3_usr"]
    TS3_PWD = config["ts3_pwd"]
    TS3_SRV = config["ts3_srv"]
    STEAM_API_KEY = config["steam_api_key"]
    STEAM_IDS = [str(sid) for sid in config["steam_ids"]]

    newdb = not os.path.exists(DB_FILE)
    con = sqlite3.connect(DB_FILE)
    if newdb:
        print("File '{}' not found. Creating new database.".format(DB_FILE))
        with open(schema_script, "rt") as f:
            schema = f.read()
        con.executescript(schema)
        c = con.cursor()
        c.execute("insert into user (username, firstname, telegram_id, added, beg, admin) values "
                  "('Admin', 'Admin', ?, datetime('now'), 1, 1)", (ADMIN_ID, ))
        con.commit()
        c.close()
    else:
        print("Using database '{}'.".format(DB_FILE))
    c = con.cursor()
    c.execute("insert into session (start, end) values (datetime('now'), datetime('now'));")
    SESSION_ID = c.lastrowid
    con.commit()
    c.execute("select telegram_id from user")
    KNOWN_USERS = {u for (u, ) in c.fetchall()}
    c.close()
    con.close()


def send_keep_alive(session_id):
    """
        Saves the current time to the database to keep track of the last known working time in case the bot crashed.

        @param session_id The ID of the current bot session.
    """
    con = sqlite3.connect(DB_FILE)
    con.execute("update session set end = datetime('now') where id=?", (session_id, ))
    con.commit()
    con.close()


def get_session(session_id):
    """
        Gets information (start time, end time, and duration about the current session by session_id.

        @param session_id The ID of the current bot session.
    """
    con = sqlite3.connect(DB_FILE)
    c = con.cursor()
    c.execute("select id, start, end, strftime('%s', end) - strftime('%s', start) as duration from session where id=?",
              (session_id, ))
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
    con = sqlite3.connect(DB_FILE)
    c = con.cursor()
    c.execute("update user set bday = ? where id = ?", (bday, user_id))
    con.commit()
    c.execute("select username, firstname, telegram_id from user where id = ?", (user_id, ))
    result = c.fetchone()
    c.close()
    con.close()
    return result


def add_user(user):
    """
        Adds the given user to the database and the KNOWN_USERS dictionary.

        @param user The user as defined by the telegram module.
    """
    global KNOWN_USERS
    con = sqlite3.connect(DB_FILE)
    c = con.cursor()
    c.execute("insert into user (username, firstname, lastname, telegram_id, added, beg, admin) values "
              "(?, ?, ?, ?, datetime('now'), 0, 0)", (user.username, user.first_name, user.last_name, user.id))
    con.commit()
    c.close()
    con.close()
    KNOWN_USERS[user.id] = 1


def get_user_by_id(user_id):
    """
        Returns information (username, first name, last name, telegram id)) about a user identified by his
        user_id (not telegram id!).

        @param user_id The user id as it is in the database.
    """
    con = sqlite3.connect(DB_FILE)
    c = con.cursor()
    c.execute("select username, firstname, lastname, telegram_id from user where id=?", (user_id, ))
    result = c.fetchone()
    c.close()
    con.close()
    return result


def get_all_users():
    """
        Returns a list of all users in the database.
    """
    con = sqlite3.connect(DB_FILE)
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
    con = sqlite3.connect(DB_FILE)
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
    con = sqlite3.connect(DB_FILE)
    con.execute("update user set beg = 1 where id=?", (user_id, ))
    con.commit()
    con.close()


def is_admin(telegram_id):
    """
        Checks if the user with the given telegram id has administrator permissions.

        @param telegram_id The users telegram id.
    """
    con = sqlite3.connect(DB_FILE)
    c = con.cursor()
    c.execute("select count(id) from user where admin=1 and telegram_id=?", (telegram_id, ))
    (result, ) = c.fetchone()
    c.close()
    con.close()
    return result


def is_beg(telegram_id):
    """
        Checks if the user with the given telegram id is tagged as a BEG member.

        @param telegram_id The users telegram id.
    """
    con = sqlite3.connect(DB_FILE)
    c = con.cursor()
    c.execute("select count(id) from user where beg=1 and telegram_id=?", (telegram_id, ))
    (result, ) = c.fetchone()
    c.close()
    con.close()
    return result


def check_for_birthdays():
    """
        Checks if one or more of the bouncing egg members have a birthday today and returns a list of strings
        corresponding to birthday wishes for each user with a birthday today.
    """
    con = sqlite3.connect(DB_FILE)
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
                        msg = "{}  {}  {}  Happy Birthday, {}!  {}  {}  {}".format(emoji_party_cone, emoji_sparkle,
                                                                                   emoji_balloon, r[1], emoji_balloon,
                                                                                   emoji_cake, emoji_present)
                        msgs.append(msg)
                except ValueError:
                    print("Encountered malformed birthday for user id {}, please check and correct.".format(r[0]))
    return msgs


def get_steam_status():
    """
        Connects to the Steam Web API as defined in the configuration file and returns a string
        resembling the currently online users in steam, or None if the request failed.
    """
    states = {
        0:  "Offline",
        1:  "Online",
        2:  "Busy",
        3:  "Away",
        4:  "Snooze",
        5:  "Looking to Trade",
        6:  "Looking to Play"
    }

    site = urllib.request.urlopen("http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={}&steamids={}"
                                  .format(STEAM_API_KEY, ",".join(STEAM_IDS)))
    content = site.read()
    try:
        data = json.loads(content.decode("utf-8"))
        pinfo = []
        for p in data["response"]["players"]:
            if p["personastate"] != 0:
                pstate = states[p["personastate"]]
                if "gameid" in p:
                    pstate = "{} / InGame".format(pstate)
                pinfo.append("{} {} {}".format(p["personaname"], emoji_squiggly_line, pstate))
        if len(pinfo) > 0:
            return "{}{} Steam {}{}\n{} {}".format(emoji_thick_dash, emoji_thick_dash, emoji_thick_dash,
                                                   emoji_thick_dash, emoji_orange_rhombus,
                                                   "\n{} ".format(emoji_orange_rhombus).join(pinfo))
        else:
            return "{}{} Steam {}{}\nThere's nobody online {}".format(emoji_thick_dash, emoji_thick_dash,
                                                                      emoji_thick_dash, emoji_thick_dash, emoji_sad)

    except ValueError:
        print("Error: Steam API sent empty response.")

    return "{}{} Steam {}{}\nThe Steam API sent nothing {}".format(emoji_thick_dash, emoji_thick_dash,
                                                                   emoji_thick_dash, emoji_thick_dash, emoji_sad)


def get_ts3_status():
    """
        Connects to the Teamspeak 3 server as defined in the configuration file and returns a string
        resembling the currently online users.
    """
    ts3con = ts3.query.TS3Connection(TS3_SRV)

    channels = {}
    clients = []

    try:
        ts3con.login(client_login_name=TS3_USR, client_login_password=TS3_PWD)
        ts3con.use(sid=1)

        resp = ts3con.clientlist()
        for client in resp.parsed:
            if not client["client_nickname"].startswith("{} from ".format(TS3_USR)):
                channels[client["cid"]] = 0
                clients.append((client["client_nickname"], client["cid"]))

        if len(clients) == 0:
            return "{}{} TeamSpeak 3 {}{}\n There's nobody online {}".format(emoji_thick_dash, emoji_thick_dash,
                                                                             emoji_thick_dash, emoji_thick_dash,
                                                                             emoji_sad)

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
                if client == len(channels[c]["clients"])-1:
                    clientlines.append(" {} {} {}".format(emoji_crossing_l, emoji_blue_ball,
                                                          channels[c]["clients"][client]))
                else:
                    clientlines.append(" {} {} {}".format(emoji_crossing_t, emoji_blue_ball,
                                                          channels[c]["clients"][client]))

            entries.append("{} {}\n{}".format(emoji_speech_bubble, channels[c]["name"], "\n".join(clientlines)))

        return "{}{} TeamSpeak 3 {}{}\n{}".format(emoji_thick_dash, emoji_thick_dash, emoji_thick_dash,
                                                  emoji_thick_dash, "\n".join(entries))

    except ts3.query.TS3QueryError as err:
        print("TS3 query failed:", err.resp.error["msg"])
        return "{} TS3 Error {}".format(emoji_bang, emoji_bang)


if __name__ == "__main__":
    main()
