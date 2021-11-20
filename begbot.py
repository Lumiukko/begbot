"""
This is the Bouncing Egg Telegram Bot.
"""

from telegram.ext import Updater, CommandHandler, Job, MessageHandler, Filters
from telegram.chataction import ChatAction
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

    version = "0.13"

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
        self.dp.add_handler(MessageHandler(Filters.location, self.process_location))
        self.dp.add_handler(CommandHandler("ts3", self.ts3_info))
        self.dp.add_handler(CommandHandler("session", self.session_info))
        self.dp.add_handler(CommandHandler("listusers", self.list_users))
        self.dp.add_handler(CommandHandler("steam", self.steam_info))
        self.dp.add_handler(CommandHandler("deluser", self.delete_user))
        self.dp.add_handler(MessageHandler(Filters.text & ~Filters.command, self.process_message))
        
        t = threading.Timer(10, self.send_keep_alive)


    def start(self):
        """
        Makes the bot start polling for messages.

        @return: None
        """
        self.updater.start_polling(bootstrap_retries=-1)
        self.updater.idle()

    def error(self, update, context):
        """
        Sends a warning to the logger that reports on an error occurred.

        @param update: The update at which the error occurred.
        @param error: The error that occurred
        @return: None
        """
        self.logger.warn("Update={}, Error={}".format(update, context.error))

    def is_known(self, telegram_id):
        """
        Checks whether a user with the given telegram id is known in the database.

        @param telegram_id: The users telegram id.
        @return: True if the user is known, False otherwise.
        """
        return telegram_id in self.cfg.known_users

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

    def process_message(self, update, context):
        """
        Processes a message received by the bot.

        @param update: The update that triggered the command.
        @param context: The bot context
        @return: True if successful, False otherwise.
        """

        # Checks if that user is known. If the user is not known, they will be added to the DB.
        if not self.is_known(update.message.from_user.id):
            self.add_user(update.message.from_user)

        print(update)

    def process_location(self, bot, update):
        geo_location = (update.message.location.longitude, update.message.location.latitude)

        print(geo_location)

    def add_user(self, user):
        """
        Adds a user to the local database and makes them known.

        @param user: The user represented by a dictionary with fields username, first_name, last_name, and id.
        """
        con = sqlite3.connect(self.cfg.db_file)
        c = con.cursor()
        c.execute("insert into user (username, firstname, lastname, telegram_id, added, beg, admin)"
                  " values (?, ?, ?, ?, datetime('now'), 0, 0)",
                  (user.username, user.first_name, user.last_name, user.id))
        con.commit()
        c.close()
        con.close()
        self.cfg.known_users.add(user.id)

    def delete_user(self, update, context):
        """
        Deletes a user from the local database and makes them unknown.

        
        @param update: The update that triggered the command.
        @param context: The bot context
        @return: True if successful, False otherwise.
        """
        if not self.is_admin(update.message.from_user.id):
            self.send_message_admin_only(update, context)
            return False

        command_usage_string = emoji.emojize(":anger_symbol: Command usage: /deluser <telegram id>", use_aliases=True)

        args = update.message.text.split()
        if len(args) >= 2:
            try:
                tid = int(args[1])
                if not self.is_known(tid):
                    response = emoji.emojize(":anger_symbol: No user known with telegram id '{}'.".format(tid), use_aliases=True)
                    context.bot.send_message(update.message.chat_id, text=response)
                    return False
                if self.is_admin(tid):
                    response = emoji.emojize(":anger_symbol: Can't delete the administrator.", use_aliases=True)
                    context.bot.send_message(update.message.chat_id, text=response)
                    return False
                con = sqlite3.connect(self.cfg.db_file)
                c = con.cursor()
                c.execute("delete from user where telegram_id = ?", (tid, ))
                con.commit()
                c.close()
                con.close()
                self.cfg.known_users.remove(tid)
                response = emoji.emojize(":heavy_check_mark: Deleted user with telegram id '{}'.".format(tid), use_aliases=True)
                context.bot.send_message(update.message.chat_id, text=response)
                return True
            except ValueError:
                context.bot.send_message(update.message.chat_id, text=command_usage_string)
                return False
        else:
            context.bot.send_message(update.message.chat_id, text=command_usage_string)
        return False

    def add_to_beg(self, update, context):
        """
        Sets the BEG flag for the user with the given telegram ID.

        
        @param update: The update that triggered the command.
        @param context: The bot context
        @return: True if successful, False otherwise.
        """

        if not self.is_admin(update.message.from_user.id):
            self.send_message_admin_only(update, context)
            return False

        command_usage_string = emoji.emojize(":anger_symbol: Command usage: /addbeg <telegram id>", use_aliases=True)

        args = update.message.text.split()
        if len(args) >= 2:
            try:
                tid = int(args[1])
                if not self.is_known(tid):
                    response = emoji.emojize(":anger_symbol: No user known with telegram id '{}'.".format(tid), use_aliases=True)
                    context.bot.send_message(update.message.chat_id, text=response)
                    return False

                con = sqlite3.connect(self.cfg.db_file)
                c = con.cursor()
                c.execute("update table user set beg=1 where telegram_id=?;", (tid, ))
                con.commit()
                c.close()
                con.close()

                response = emoji.emojize(":heavy_check_mark: Added user with telegram id '{}' to BEG.".format(tid), use_aliases=True)
                context.bot.send_message(update.message.chat_id, text=response)
                return True
            except ValueError:
                context.bot.send_message(update.message.chat_id, text=command_usage_string)
                return False
        else:
            context.bot.send_message(update.message.chat_id, text=command_usage_string)
        return False

    def list_users(self, update, context):
        """
        Gets user information from the database and lists all known users.

        
        @param update: The update that triggered the command.
        @param context: The bot context
        """
        if not self.is_admin(update.message.from_user.id):
            self.send_message_admin_only(update, context)
            return False

        con = sqlite3.connect(self.cfg.db_file)
        c = con.cursor()
        c.execute("select id, telegram_id, username, firstname, added, beg from user")
        result = c.fetchall()
        c.close()
        con.close()

        response = ""
        tpl = ("ID", "TID", "Username", "Name", "Added", "B")
        response += "|`{:3}`|`{:9}`|`{:15}`|`{:9}`|`{:10}`|`{}`|\n"\
            .replace("|", EEmoji.BOX_DRAWINGS_LIGHT_VERTICAL)\
            .format(tpl[0], tpl[1], tpl[2], tpl[3], tpl[4], tpl[5])

        nlf = NoneLessFormatter()
        for tpl in result:
            uname = "~"
            if tpl[2] != "":
                uname = tpl[2]
            response += nlf.format("|`{:3d}`|`{:9d}`|`{:15.15}`|`{:9.9}`|`{:10.10}`|`{}`|\n"
                                   .replace("|", EEmoji.BOX_DRAWINGS_LIGHT_VERTICAL),
                                   tpl[0], tpl[1], uname, tpl[3], tpl[4], tpl[5])

        context.bot.send_message(update.message.chat_id, text=response, parse_mode="Markdown")

    def session_info(self, update, context):
        """
        Gets information (start time, end time, and duration) about the current session.

        
        @param update: The update that triggered the command.
        @param context: The bot context
        @return: True if successful, False otherwise.
        """
        if not self.is_admin(update.message.from_user.id):
            self.send_message_admin_only(update, context)
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
        context.bot.send_message(update.message.chat_id, text=response)
        return True

    def steam_info(self, update, context):
        """
        Creates a thread that connects to the Steam API and gets information about
        all SteamIDs set in the configuration.

        
        @param update: The update that triggered the command.
        @param context: The bot context
        @return: Returns True.
        """
        if not self.is_beg(update.message.from_user.id):
            self.send_message_beg_only(update, context)
            return False

        context.bot.send_chat_action(update.message.chat_id, ChatAction.TYPING)

        logic_thread = threading.Thread(target=self.steam_info_logic, args=[update, context])
        logic_thread.start()

        return True

    def steam_info_logic(self, update, context):
        """
        Connects to the Steam API and gets information about all SteamIDs set in the configuration.

        
        @param update: The update that triggered the command.
        @param context: The bot context
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
                            self.get_steam_status_info(player["personastate"])),
                            use_aliases=True
                    )
                    if "gameid" in player:  # Player is in a game.
                        player_entry = emoji.emojize(":large_orange_diamond: {} / InGame".format(player_entry), use_aliases=True)
                    else:
                        player_entry = ":large_blue_diamond: {}".format(player_entry)
                    player_list.append(player_entry)

            if not player_list:  # All SteamIDs are offline.
                response = emoji.emojize(
                    ":heavy_minus_sign::heavy_minus_sign: Steam :heavy_minus_sign::heavy_minus_sign:\n"
                    " There's nobody online :worried_face:",
                    use_aliases=True

                )
                context.bot.send_message(update.message.chat_id, text=response)
                return True
            else:
                response = emoji.emojize(
                    ":heavy_minus_sign::heavy_minus_sign: Steam :heavy_minus_sign::heavy_minus_sign:\n"
                    "{}" .format("\n".join(player_list)),
                    use_aliases=True
                )
                context.bot.send_message(update.message.chat_id, text=response)
                return True

        except ValueError as err:
            self.logger.error("Steam API connection failed: {}".format(err))

        return False

    def ts3_info(self, update, context):
        """
        Connects to a Teamspeak 3 server, gets client information, and responds with a channel overview.

        
        @param update: The update that triggered the command.
        @param context: The bot context
        @return: Returns True if it was successful, and False if it was not.
        """

        if not self.is_beg(update.message.from_user.id):
            self.send_message_beg_only(update, context)
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
                    " There's nobody online :worried_face:",
                    use_aliases=True
                )
                context.bot.send_message(update.message.chat_id, text=response)
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
                        icon = ":mute:"
                    else:
                        icon = ":large_blue_circle:"

                    client_lines.append(" {} {} {} {}".format(prefix, icon, nickname, EEmoji.flag(country)))

                entries.append(":speech_balloon: {}\n{}".format(channels[c]["name"], "\n".join(client_lines)))

            response = emoji.emojize(
                ":heavy_minus_sign::heavy_minus_sign: TeamSpeak 3 :heavy_minus_sign::heavy_minus_sign:"
                "\n{}".format("\n".join(entries)),
                use_aliases=True
            )
            context.bot.send_message(update.message.chat_id, text=response)
            return True

        except ConnectionRefusedError as err:
            self.logger.error("TS3 connection failed: {}".format(err))
            response = emoji.emojize(":anger_symbol: TS3 Error :anger_symbol:", use_aliases=True)
            context.bot.send_message(update.message.chat_id, text=response)
            return False

        except ts3.query.TS3QueryError as err:
            self.logger.error("TS3 connection failed: {}".format(err))
            response = emoji.emojize(":anger_symbol: TS3 Error :anger_symbol:", use_aliases=True)
            context.bot.send_message(update.message.chat_id, text=response)
            return False
            
        except OSError as err:
            self.logger.error("TS3 connection failed: {}".format(err))
            response = emoji.emojize(":anger_symbol: TS3 Error :anger_symbol:", use_aliases=True)
            context.bot.send_message(update.message.chat_id, text=response)
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
            self.cfg.known_users = {u[0] for u in c.fetchall()}
            c.close()
            con.close()
            return True
        except KeyError as err:
            self.logger.error("Error: Missing field in config.json: {}".format(err))
        return False

    def send_keep_alive(self):
        """
            Saves the current time to the database to keep track of the last known working time in
            case the bot crashed.

            
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
    def send_message_admin_only(update, context):
        """
        Sends a message to the user, stating that the command is only administrators.

        
        @param update: The update that was the users command.
        @return: None
        """
        response = emoji.emojize(":anger_symbol: Sorry, only for BEGBot administrators.", use_aliases=True)
        context.bot.send_message(update.message.chat_id, text=response)

    @staticmethod
    def send_message_beg_only(update, context):
        """
        Sends a message to the user, stating that the command is only for BEG members.

        
        @param update: The update that was the users command.
        @return: None
        """
        response = emoji.emojize(":anger_symbol: Sorry, only for Bouncing Egg members.", use_aliases=True)
        context.bot.send_message(update.message.chat_id, text=response)
