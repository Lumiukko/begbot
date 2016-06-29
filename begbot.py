"""
This is the Bouncing Egg Telegram Bot.
"""

# from uuid import uuid4
# from telegram import InlineQueryResultArticle, InputTextMessageContent, ParseMode
# from telegram.ext import MessageHandler, Filters, InlineQueryHandler
from telegram.ext import Updater, CommandHandler
import logging
import json
import ts3.query
from botconfig import BotConfig
from extended_emoji import ExtendedEmoji as Emoji


class BEGBot:

    def __init__(self):
        self.cfg = BotConfig(json.load(open("config.json", "r")))
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.updater = Updater(self.cfg.token)
        self.dp = self.updater.dispatcher
        self.dp.add_error_handler(self.error)
        # self.dp.add_handler(InlineQueryHandler(self.inline_query))
        # self.dp.add_handler(MessageHandler([Filters.text], self.message))
        self.dp.add_handler(CommandHandler("ts3", self.ts3_info))

    def start(self):
        self.updater.start_polling()
        self.updater.idle()

    def error(self, update, error):
        self.logger.warn("Error: Update={}, Error={}".format(update, error))

    def ts3_info(self, bot, update):
        """
        Connects to a Teamspeak 3 server, gets client information, and responds with a channel overview.

        @param bot: The Telegram bot instance.
        @param update: The Upate that triggered the command.
        @return: Returns True if it was successful, and False if it was not.
        """

        try:
            ts3_connection = ts3.query.TS3Connection(self.cfg.ts3_srv)
            ts3_connection.login(client_login_name=self.cfg.ts3_usr,
                                 client_login_password=self.cfg.ts3_pwd)
            ts3_connection.use(sid=1)
            client_list = ts3_connection.clientlist()

            channels = {}
            clients = []

            for client in client_list.parsed:
                if not client["client_nickname"].startswith("{} from ".format(self.cfg.ts3_usr)):
                    channels[client["cid"]] = 0
                    clients.append((client["client_nickname"], client["cid"]))

            if len(clients) == 0:
                response = "{}{} TeamSpeak 3 {}{}\n There's nobody online {}" \
                    .format(Emoji.HEAVY_MINUS_SIGN, Emoji.HEAVY_MINUS_SIGN, Emoji.HEAVY_MINUS_SIGN,
                            Emoji.HEAVY_MINUS_SIGN, Emoji.WORRIED_FACE)
                bot.sendMessage(update.message.chat_id, text=response)
                return True

            channel_list = ts3_connection.channellist()
            for channel in channel_list.parsed:
                if channel["cid"] in channels:
                    channels[channel["cid"]] = {"name": channel["channel_name"], "clients": []}

            for (cname, cid) in clients:
                channels[cid]["clients"].append(cname)

            entries = []
            for c in channels:
                clientlines = []
                for client in range(0, len(channels[c]["clients"])):
                    if client == len(channels[c]["clients"]) - 1:
                        prefix = Emoji.BOX_DRAWINGS_LIGHT_UP_AND_RIGHT
                    else:
                        prefix = Emoji.BOX_DRAWINGS_LIGHT_VERTICAL_AND_RIGHT
                    clientlines.append(" {} {} {}".format(prefix, Emoji.LARGE_BLUE_CIRCLE,
                                                          channels[c]["clients"][client]))

                entries.append("{} {}\n{}".format(Emoji.SPEECH_BALLOON, channels[c]["name"],
                                                  "\n".join(clientlines)))

            response = "{}{} TeamSpeak 3 {}{}\n{}".format(Emoji.HEAVY_MINUS_SIGN, Emoji.HEAVY_MINUS_SIGN,
                                                          Emoji.HEAVY_MINUS_SIGN, Emoji.HEAVY_MINUS_SIGN,
                                                          "\n".join(entries))
            bot.sendMessage(update.message.chat_id, text=response)
            return True

        except ConnectionRefusedError as err:
            print("TS3 connection failed: {}".format(err))
            response = "{} TS3 Error {}".format(Emoji.ANGER_SYMBOL, Emoji.ANGER_SYMBOL)
            bot.sendMessage(update.message.chat_id, text=response)
            return False

        except ts3.query.TS3QueryError as err:
            print("TS3 query failed:", err.resp.error["msg"])
            response = "{} TS3 Error {}".format(Emoji.ANGER_SYMBOL, Emoji.ANGER_SYMBOL)
            bot.sendMessage(update.message.chat_id, text=response)
            return False

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
