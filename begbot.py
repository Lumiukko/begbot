import telegram
import ts3
import time
import datetime
import os
import sqlite3
import json
import random


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


# Global variables for messages
msg_only_for_admins = "{} Sorry, only for bot administrators.".format(emoji_bang)




def main():
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

    while(True):
        loop(bot) # this includes a few seconds timeout
        send_keep_alive(SESSION_ID)


def loop(bot):
    global LAST_UPDATE_ID

    for u in bot.getUpdates(offset=LAST_UPDATE_ID, timeout=6):
        message_text = u.message.text.encode('utf-8')
        sender = u.message.from_user.id

        if sender not in KNOWN_USERS:
            add_user(u.message.from_user)

        #print("Received Message from {}: {}".format(sender, message_text))


        # Public string matching
        response = match_text(message_text)
        if response != None:
            bot.sendMessage(chat_id=u.message.chat_id, text=response)


        # BEG only commands
        # Maybe check if u.message.chat.type == "private" or "group", if necessary.
        if message_text == b"/ts3":
            if is_beg(sender):
                get_ts3_status()
                #print("TS3 Status Request received.")
                ts3status = get_ts3_status()
                bot.sendMessage(chat_id=u.message.chat_id, text=ts3status)
            else:
                bot.sendMessage(chat_id=u.message.chat_id, text="{} Sorry, only for Bouncing Egg members.".format(emoji_bang))


        # Admin only commands
        if message_text == b"/session":
            if is_admin(sender):
                (s_id, s_start, s_end, s_duration) = get_session(SESSION_ID)
                bot.sendMessage(chat_id=u.message.chat_id, text="Session: id={}, start={}, lastka={}, duration={}s".format(s_id, s_start, s_end, s_duration))
            else:
                bot.sendMessage(chat_id=u.message.chat_id, text=msg_only_for_admins)

        if message_text == b"/listnonbeg":
            if is_admin(sender):
                nonbeg = "\n".join([str(u) for u in get_non_beg_users()])
                bot.sendMessage(chat_id=u.message.chat_id, text="Non-BEG Users:\n{}".format(nonbeg))
            else:
                bot.sendMessage(chat_id=u.message.chat_id, text=msg_only_for_admins)

        if message_text.startswith(b"/addbeg "):
            if is_admin(sender):
                try:
                    uid = int(message_text[8:])
                    uinfo = get_user_by_id(uid)
                    if uinfo == None:
                        bot.sendMessage(chat_id=u.message.chat_id, text="{} Error. Unknown user ID.".format(emoji_bang))
                    else:
                        add_user_to_beg(uid)
                        bot.sendMessage(chat_id=u.message.chat_id, text="{} Successfully added: {} ({}) {} Welcome! {}".format(emoji_party_ball, uinfo[1], uinfo[3], emoji_sparkle, emoji_party_cone))
                except ValueError:
                    bot.sendMessage(chat_id=u.message.chat_id, text="{} Error. Malformed user ID.".format(emoji_bang))
            else:
                bot.sendMessage(chat_id=u.message.chat_id, text=msg_only_for_admins)


        LAST_UPDATE_ID = u.update_id + 1




def match_text(text):
    # That's what she said matching... simplex, change later into a more sophisticated matching...
    twss = b"\xef\xbb\xbf \xcd\xa1\xc2\xb0 \xcd\x9c\xca\x96 \xcd\xa1\xc2\xb0".decode("utf-8")
    twss = "That's what she said ({})".format(twss)
    wordbag = "zu aber riesig passt gross groß wow lang ui eng klein nie"
    wordbag = wordbag.split()
    textbag = text.decode("utf-8").split()
    hits = 0
    for w in wordbag:
        if w in textbag:
            hits += 1
    threshold = random.randint(3, 3+int(len(textbag)/2))
    if hits >= threshold:
        return twss

    return None



def load_config():
    global KNOWN_USERS
    global SESSION_ID
    global DB_FILE
    global ADMIN_ID
    global BEG_ID
    global TOKEN
    global TS3_PWD
    global TS3_USR
    global TS3_SRV

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


    newdb = not os.path.exists(DB_FILE)
    con = sqlite3.connect(DB_FILE)
    if newdb:
        print("File '{}' not found. Creating new database.".format(DB_FILE))
        with open(schema_script, "rt") as f:
            schema = f.read()
        con.executescript(schema)
        c = con.cursor()
        c.execute("insert into user (username, firstname, telegram_id, added, beg, admin) values ('Admin', 'Admin', ?, datetime('now'), 1, 1)", (ADMIN_ID, ))
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
    con = sqlite3.connect(DB_FILE)
    con.execute("update session set end = datetime('now') where id=?", (session_id, ))
    con.commit()
    con.close()

def get_session(session_id):
    con = sqlite3.connect(DB_FILE)
    c = con.cursor()
    c.execute("select id, start, end, strftime('%s', end) - strftime('%s', start) as duration from session where id=?", (session_id, ))
    result = c.fetchone()
    c.close()
    con.close()
    return result


def add_user(user):
    con = sqlite3.connect(DB_FILE)
    c = con.cursor()
    c.execute("insert into user (username, firstname, lastname, telegram_id, added, beg, admin) values (?, ?, ?, ?, datetime('now'), 0, 0)", (user.username, user.first_name, user.last_name, user.id))
    con.commit()
    c.close()
    con.close()

def get_user_by_id(id):
    con = sqlite3.connect(DB_FILE)
    c = con.cursor()
    c.execute("select username, firstname, lastname, telegram_id from user where id=?", (id, ))
    result = c.fetchone()
    c.close()
    con.close()
    return result

def get_non_beg_users():
    con = sqlite3.connect(DB_FILE)
    c = con.cursor()
    c.execute("select id, username, firstname, lastname, telegram_id from user where beg != 1")
    result = c.fetchall()
    c.close()
    con.close()
    return result

def add_user_to_beg(id):
    con = sqlite3.connect(DB_FILE)
    con.execute("update user set beg = 1 where id=?", (id, ))
    con.commit()
    con.close()

def is_admin(telegram_id):
    con = sqlite3.connect(DB_FILE)
    c = con.cursor()
    c.execute("select count(id) from user where admin=1 and telegram_id=?", (telegram_id, ))
    (result, ) = c.fetchone()
    c.close()
    con.close()
    return result


def is_beg(telegram_id):
    con = sqlite3.connect(DB_FILE)
    c = con.cursor()
    c.execute("select count(id) from user where beg=1 and telegram_id=?", (telegram_id, ))
    (result, ) = c.fetchone()
    c.close()
    con.close()
    return result


def get_ts3_status():
    ts3con = ts3.query.TS3Connection(TS3_SRV)

    channels = {}
    clients = []




    'Awesome Booth 3\n  \xf0\x9f\x94\xb5 makko\n  \xf0\x9f\x94\xb5 ZIP-Drive'

    try:
        ts3con.login(client_login_name=TS3_USR, client_login_password=TS3_PWD)
        ts3con.use(sid=1)

        resp = ts3con.clientlist()
        for client in resp.parsed:
            if not client["client_nickname"].startswith("{} from ".format(TS3_USR)):
                channels[client["cid"]] = 0
                clients.append( (client["client_nickname"], client["cid"]) )

        if len(clients) == 0:
            return "{}{} TeamSpeak 3 {}{}\n There's nobody online {}".format(emoji_thick_dash, emoji_thick_dash, emoji_thick_dash, emoji_thick_dash, emoji_sad)

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
                    clientlines.append(" {} {} {}".format(emoji_crossing_l, emoji_blue_ball, channels[c]["clients"][client]))
                else:
                    clientlines.append(" {} {} {}".format(emoji_crossing_t, emoji_blue_ball, channels[c]["clients"][client]))

            entries.append("{} {}\n{}".format(emoji_speech_bubble, channels[c]["name"], "\n".join(clientlines)))

        return "{}{} TeamSpeak 3 {}{}\n{}".format(emoji_thick_dash, emoji_thick_dash, emoji_thick_dash, emoji_thick_dash, "\n".join(entries))

    except ts3.query.TS3QueryError as err:
        print("TS3 query failed:", err.resp.error["msg"])
        return "{} TS3 Error {}".format(emoji_bang, emoji_bang)





if __name__ == "__main__":
    main()