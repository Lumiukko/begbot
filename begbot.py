"""
This is the Bouncing Egg Telegram Bot.
"""

# from uuid import uuid4
# from telegram import InlineQueryResultArticle, InputTextMessageContent, ParseMode
# from telegram.ext import MessageHandler, Filters, InlineQueryHandler
from telegram.ext import Updater, CommandHandler, Job
import logging
import os
import json
import ts3.query
import urllib.request
import urllib.error
from botconfig import BotConfig
import emoji
from extended_emoji import ExtendedEmoji as EEmoji
from noneless_formatter import NoneLessFormatter
import sqlite3
import threading


class BEGBot:

    version = "0.1"

    def __init__(self):
        self.cfg = BotConfig(json.load(open("config.json", "r")))
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.init_db()
        self.logger.info("SessionID: {}".format(self.cfg.session_id))

        self.updater = Updater(self.cfg.token)
        self.dp = self.updater.dispatcher
        self.dp.add_error_handler(self.error)
        # self.dp.add_handler(InlineQueryHandler(self.inline_query))
        # self.dp.add_handler(MessageHandler([Filters.text], self.message))
        self.dp.add_handler(CommandHandler("ts3", self.ts3_info))
        self.dp.add_handler(CommandHandler("session", self.session_info))
        self.dp.add_handler(CommandHandler("listusers", self.list_users))
        self.dp.add_handler(CommandHandler("steam", self.steam_info))

        keep_alive_job = Job(self.send_keep_alive, interval=3, repeat=True)
        self.dp.job_queue.put(keep_alive_job)

    def start(self):
        """
        Makes the bot start polling for messages.

        @return: None
        """
        self.updater.start_polling()
        self.updater.idle()

    def error(self, update, error):
        """
        Sends a warning to the logger that reports on an error occurred.

        @param update: The update at which the error occurred.
        @param error: The error that occurred
        @return: None
        """
        self.logger.warn("Update={}, Error={}".format(update, error))

    def is_known(self, telegram_id):
        """
        Checks whether a user with the given telegram id is known in the database.

        @param telegram_id: The users telegram id.
        @return: True if the user is known, False otherwise.
        """
        con = sqlite3.connect(self.cfg.db_file)
        c = con.cursor()
        c.execute("select count(id) from user where telegram_id=?", (telegram_id, ))
        (result, ) = c.fetchone()
        c.close()
        con.close()
        return result

    def is_beg(self, telegram_id):
        """
        Checks if the user with the given telegram id is tagged as a BEG member.

        @param telegram_id The users telegram id.
        @return: True if the user is tagged as a BEG member, False otherwise
        """
        con = sqlite3.connect(self.cfg.db_file)
        c = con.cursor()
        c.execute("select count(id) from user where beg=1 and telegram_id=?", (telegram_id, ))
        (result, ) = c.fetchone()
        c.close()
        con.close()
        return result

    def is_admin(self, telegram_id):
        """
            Checks if the user with the given telegram id has administrator permissions.

            @param telegram_id The users telegram id.
        """
        con = sqlite3.connect(self.cfg.db_file)
        c = con.cursor()
        c.execute("select count(id) from user where admin=1 and telegram_id=?", (telegram_id, ))
        (result, ) = c.fetchone()
        c.close()
        con.close()
        return result

    def add_to_beg(self, bot, update):
        """
        Sets the BEG flag for the user with the given telegram ID.

        @param bot: The Telegram bot instance.
        @param update: The update that triggered the command.
        @return: True if successful, False otherwise.
        """
        if not self.is_admin(update.message.from_user.id):
            self.send_message_admin_only(bot, update)
            return False

        telegram_id = update.message.text

        if telegram_id is None:
            return False

        if not self.is_known(telegram_id):
            return False

        con = sqlite3.connect(self.cfg.db_file)
        c = con.cursor()
        c.execute("update table user set beg=1 where telegram_id=?;", (telegram_id, ))
        con.commit()
        c.close()
        con.close()
        return True

    def list_users(self, bot, update):
        """
        Gets user information from the database and lists all known users.

        @param bot: The Telegram bot instance.
        @param update: The update that triggered the command.
        """
        if not self.is_admin(update.message.from_user.id):
            self.send_message_admin_only(bot, update)
            return False

        con = sqlite3.connect(self.cfg.db_file)
        c = con.cursor()
        c.execute("select id, telegram_id, username, firstname, added, beg, admin from user")
        result = c.fetchall()
        c.close()
        con.close()

        response = ""
        tpl = ("ID", "TID", "Username", "Name", "Added", "B", "A")
        response += "|`{:3}`|`{:9}`|`{:15}`|`{:9}`|`{:10}`|`{}`|`{}`|\n"\
            .replace("|", EEmoji.BOX_DRAWINGS_LIGHT_VERTICAL)\
            .format(tpl[0], tpl[1], tpl[2], tpl[3], tpl[4], tpl[5], tpl[6])

        nlf = NoneLessFormatter()
        for tpl in result:
            uname = "~"
            if tpl[2] != "":
                uname = tpl[2]
            response += nlf.format("|`{:3d}`|`{:9d}`|`{:15.15}`|`{:9.9}`|`{:10.10}`|`{}`|`{}`|\n"
                                   .replace("|", EEmoji.BOX_DRAWINGS_LIGHT_VERTICAL),
                                   tpl[0], tpl[1], uname, tpl[3], tpl[4], tpl[5], tpl[6])

        bot.sendMessage(update.message.chat_id, text=response, parse_mode="Markdown")

    def session_info(self, bot, update):
        """
        Gets information (start time, end time, and duration) about the current session.

        @param bot: The Telegram bot instance.
        @param update: The update that triggered the command.
        @return: True if successful, False otherwise.
        """
        if not self.is_admin(update.message.from_user.id):
            self.send_message_admin_only(bot, update)
            return False

        con = sqlite3.connect(self.cfg.db_file)
        c = con.cursor()
        c.execute("select id, start, end, strftime('%s', end) - strftime('%s', start) as duration "
                  "from session where id=?",
                  (self.cfg.session_id, ))
        result = c.fetchone()
        c.close()
        con.close()
        response = "BEGBot [{}], Session: id={}, start={}, lastka={}, duration={}".format(
            self.version, result[0], result[1], result[2], result[3])
        bot.sendMessage(update.message.chat_id, text=response)
        return True

    def steam_info(self, bot, update):
        """
        Creates a thread that connects to the Steam API and gets information about all SteamIDs set in the configuration.

        @param bot: The Telegram bot instance.
        @param update: The update that triggered the command.
        @return: Returns True.
        """
        if not self.is_beg(update.message.from_user.id):
            self.send_message_beg_only(bot, update)
            return False

        logic_thread = threading.Thread(target=self.steam_info_logic, args=[bot, update])
        logic_thread.start()

        return True

    def steam_info_logic(self, bot, update):
        """
        Connects to the Steam API and gets information about all SteamIDs set in the configuration.

        @param bot: The Telegram bot instance.
        @param update: The update that triggered the command.
        @return: Returns True if it was successful, and False if it was not.
        """
        steam_id_string = ",".join(map(str, self.cfg.steam_ids))
        site = urllib.request.urlopen(self.cfg.steam_api_url.format(self.cfg.steam_api_key, steam_id_string))
        site_content = site.read()
        try:
            data = json.loads(site_content.decode("utf-8"))
            player_list = []
            for player in data["response"]["players"]:
                if player["personastate"] != 0:  # Only show non-offline players.
                    player_entry = emoji.emojize("{} :wavy_dash: {}".format(
                            player["personaname"],
                            self.get_steam_status_info(player["personastate"]))
                    )
                    if "gameid" in player:  # Player is in a game.
                        player_entry = emoji.emojize(":large_orange_diamond: {} / InGame".format(player_entry))
                    else:
                        player_entry = ":large_blue_diamond: {}".format(player_entry)
                    player_list.append(player_entry)

            if not player_list:  # All SteamIDs are offline.
                response = emoji.emojize(
                    ":heavy_minus_sign::heavy_minus_sign: Steam :heavy_minus_sign::heavy_minus_sign:\n"
                    " There's nobody online :worried_face:"
                )
                bot.sendMessage(update.message.chat_id, text=response)
                return True
            else:
                response = emoji.emojize(
                    ":heavy_minus_sign::heavy_minus_sign: Steam :heavy_minus_sign::heavy_minus_sign:\n"
                    "{}" .format("\n".join(player_list))
                )
                bot.sendMessage(update.message.chat_id, text=response)
                return True

        except ValueError as err:
            self.logger.error("Steam API connection failed: {}".format(err))

        return False

    def ts3_info(self, bot, update):
        """
        Connects to a Teamspeak 3 server, gets client information, and responds with a channel overview.

        @param bot: The Telegram bot instance.
        @param update: The update that triggered the command.
        @return: Returns True if it was successful, and False if it was not.
        """

        if not self.is_beg(update.message.from_user.id):
            self.send_message_beg_only(bot, update)
            return False

        try:
            ts3_connection = ts3.query.TS3Connection(self.cfg.ts3_srv)
            ts3_connection.login(client_login_name=self.cfg.ts3_usr,
                                 client_login_password=self.cfg.ts3_pwd)
            ts3_connection.use(sid=1)
            client_list = ts3_connection.clientlist(away=True, voice=True, country=True)

            channels = {}
            clients = []

            for client in client_list.parsed:
                if not client["client_nickname"].startswith("{} from ".format(self.cfg.ts3_usr)):
                    channels[client["cid"]] = 0
                    client_muted = client["client_input_muted"] == "1"
                    clients.append((client["client_nickname"], client["cid"],
                                    client_muted, client["client_country"]))

            if not clients:
                response = emoji.emojize(
                    ":heavy_minus_sign::heavy_minus_sign: TeamSpeak 3 :heavy_minus_sign::heavy_minus_sign:\n"
                    " There's nobody online :worried_face:"
                )
                bot.sendMessage(update.message.chat_id, text=response)
                return True

            channel_list = ts3_connection.channellist()
            for channel in channel_list.parsed:
                if channel["cid"] in channels:
                    channels[channel["cid"]] = {"name": channel["channel_name"], "clients": []}

            for (cname, cid, muted, country) in clients:
                channels[cid]["clients"].append((cname, muted, country))

            entries = []
            for c in channels:
                client_lines = []
                for client in range(0, len(channels[c]["clients"])):
                    (nickname, muted, country) = channels[c]["clients"][client]

                    if client == len(channels[c]["clients"]) - 1:
                        prefix = EEmoji.BOX_DRAWINGS_LIGHT_UP_AND_RIGHT
                    else:
                        prefix = EEmoji.BOX_DRAWINGS_LIGHT_VERTICAL_AND_RIGHT
                    if muted:
                        icon = ":speaker_with_cancellation_stroke:"
                    else:
                        icon = ":large_blue_circle:"

                    client_lines.append(" {} {} {} {}".format(prefix, icon, nickname, EEmoji.flag(country)))

                entries.append(":speech_balloon: {}\n{}".format(channels[c]["name"], "\n".join(client_lines)))

            response = emoji.emojize(
                ":heavy_minus_sign::heavy_minus_sign: TeamSpeak 3 :heavy_minus_sign::heavy_minus_sign:"
                "\n{}".format("\n".join(entries))
            )
            bot.sendMessage(update.message.chat_id, text=response)
            return True

        except ConnectionRefusedError as err:
            self.logger.error("TS3 connection failed: {}".format(err))
            response = emoji.emojize(":anger_symbol: TS3 Error :anger_symbol:")
            bot.sendMessage(update.message.chat_id, text=response)
            return False

        except ts3.query.TS3QueryError as err:
            self.logger.error("TS3 connection failed: {}".format(err))
            response = emoji.emojize(":anger_symbol: TS3 Error :anger_symbol:")
            bot.sendMessage(update.message.chat_id, text=response)
            return False

    def init_db(self):
        """
        Gets basic configuration from local database or creates it according
        to a given schema, if it does not exist.

        @return: True if database creation/connection was successful, False otherwise.
        """
        try:
            new_db = not os.path.exists(self.cfg.db_file)
            con = sqlite3.connect(self.cfg.db_file)
            if new_db:
                self.logger.info("File '{}' not found. Creating new database.".format(self.cfg.db_file))

                with open(self.cfg.db_schema, "rt") as f:
                    schema = f.read()
                con.executescript(schema)
                c = con.cursor()
                c.execute("insert into user (username, firstname, telegram_id, added, beg, admin) values "
                          "('Admin', 'Admin', ?, datetime('now'), 1, 1)", (self.cfg.admin_id, ))
                con.commit()
                c.close()
            else:
                self.logger.info("Using database '{}'.".format(self.cfg.db_file))
            c = con.cursor()
            c.execute("insert into session (start, end) values (datetime('now'), datetime('now'));")
            self.cfg.session_id = c.lastrowid
            con.commit()
            c.execute("select telegram_id from user")
            self.cfg.known_users = {u for u in c.fetchall()}
            c.close()
            con.close()
            return True
        except KeyError as err:
            self.logger.error("Error: Missing field in config.json: {}".format(err))
        return False

    def send_keep_alive(self, bot, job):
        """
            Saves the current time to the database to keep track of the last known working time in
            case the bot crashed.

            @param bot: The Telegram bot instance.
            @param job: The Job instance for the bots job queue.
        """
        con = sqlite3.connect(self.cfg.db_file)
        con.execute("update session set end = datetime('now') where id=?", (self.cfg.session_id, ))
        con.commit()
        con.close()

    @staticmethod
    def get_steam_status_info(status):
        """
        Returns a textual representation of the steam status number.

        @param status: The status number as an integer between 0 and 6
        @return: Returns the name of the given status.
        """
        return {
            0: "Offline",
            1: "Online",
            2: "Busy",
            3: "Away",
            4: "Snooze",
            5: "Looking to Trade",
            6: "Looking to Play"
        }[status]

    @staticmethod
    def send_message_admin_only(bot, update):
        """
        Sends a message to the user, stating that the command is only administrators.

        @param bot: The Telegram bot instance.
        @param update: The update that was the users command.
        @return: None
        """
        response = emoji.emojize(":anger_symbol: Sorry, only for BEGBot administrators.")
        bot.sendMessage(update.message.chat_id, text=response)

    @staticmethod
    def send_message_beg_only(bot, update):
        """
        Sends a message to the user, stating that the command is only for BEG members.

        @param bot: The Telegram bot instance.
        @param update: The update that was the users command.
        @return: None
        """
        response = emoji.emojize(":anger_symbol: Sorry, only for Bouncing Egg members.")
        bot.sendMessage(update.message.chat_id, text=response)









"""
    # These are example inline and message handlers, not used yet.

    def inline_query(self, bot, update):
        print("Inline Query: {}".format(update))

        query = update.inline_query.query
        results = list()

        results.append(InlineQueryResultArticle(id=uuid4(),
                                                title="Test1",
                                                input_message_content=InputTextMessageContent("Test1")))

        results.append(InlineQueryResultArticle(id=uuid4(),
                                                title="Test2",
                                                input_message_content=InputTextMessageContent("Test222222")))

        bot.answerInlineQuery(update.inline_query.id, results=results)

    def message(self, bot, update):
        print("Update: {}".format(update))
"""
