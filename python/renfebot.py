#!/usr/local/bin/python3

from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler,
                          Filters, RegexHandler, ConversationHandler)
from telegram.ext import CallbackQueryHandler
from telegram.parsemode import ParseMode

import datetime
from enum import Enum
import logging

from telegramcalendarkeyboard import telegramcalendar
import renfechecker
import renfebotdb
from renfebottexts import texts as TEXTS
from renfebottexts import keyboards as KEYBOARDS
from bot_data import TOKEN, ADMIN_ID


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)


class ConvStates(Enum):
    OPTION = 1
    STATION = 2
    DATE = 3


class BotOptions(Enum):
    ADD_QUERY = 1
    DEL_QUERY = 2
    DO_QUERY = 3


class RenfeBot:
    class Conversation:
        def __init__(self, userid):
            self._userid = userid
            self.reset()

        def reset(self):
            self._option = 0
            self._origin = None
            self._dest = None
            self._date = None

    def __init__(self, token, admin_id):
        self._token = token
        self._admin_id = admin_id
        self._updater = Updater(token)
        self._install_handlers()
        self._conversations = {}
        self._RF = renfechecker.RenfeChecker()
        self._DB = renfebotdb.RenfeBotDB("midatabase.db")

    def _send_query_results_to_user(self, bot, userid, results, origin, dest, date):
        if results[0]:
            logger.debug("Returning data to user")
            df = results[1]
            trenes = df.loc[df["DISPONIBLE"] == True]
            logger.debug("Obtained trenes")
            bot.send_message(chat_id=userid, text=TEXTS["FOUND_N_TRAINS"].
                             format(ntrains=trenes.shape[0], origin=origin, destination=dest, date=date))
            for index, train in trenes.iterrows():
                bot.send_message(chat_id=userid,
                                 text=TEXTS["TRAIN_INFO"].format(
                                     t_departure=train.SALIDA.strftime(
                                         "%H:%M"),
                                     t_arrival=train.LLEGADA.strftime("%H:%M"),
                                     cost=train.PRECIO if train.PRECIO > 50 else "*" +
                                     str(train.PRECIO) + "*",
                                     ticket_type=train.TARIFA
                                 ),
                                 parse_mode=ParseMode.MARKDOWN)
        else:
            bot.send_message(chat_id=userid, text=TEXTS["NO_TRAINS_FOUND"].format(
                origin=origin, destination=dest, date=date))

    def _h_date(self, bot, update):
        logger.debug("Processing fehcha2")
        selected, date = telegramcalendar.process_calendar_selection(
            bot, update)
        if not selected:
            logger.debug("Not selected")
            return ConvStates.DATE
        else:
            logger.debug("selected")
            userid = update.callback_query.from_user.id
            conv = self._conversations[userid]
            conv._date = date.strftime("%d/%m/%Y")
            logger.debug("Date is " + conv._date)
            bot.send_message(chat_id=userid, text=TEXTS["SELECTED_DATA"].
                             format(origin=conv._origin, destination=conv._dest, date=conv._date))
            if conv._option == BotOptions.ADD_QUERY:
                res = self._DB.add_periodic_query(
                    userid, conv._origin, conv._dest, conv._date)

            elif conv._option == BotOptions.DO_QUERY:
                res = self._RF.check_trip(conv._origin, conv._dest, conv._date)
                self._send_query_results_to_user(bot, userid, res,
                                                 conv._origin, conv._dest, conv._date)
            else:
                logger.error("Problem, no other option should lead HERE!")
        return ConversationHandler.END    

    def _h_cancel(self, bot, update):
        return ConversationHandler.END

    def _h_station(self, bot, update):
        logger.debug("Setting Station")
        userid = update.message.from_user.id
        if self._conversations[userid]._origin is None:
            logger.debug("Origin Station")
            self._conversations[userid]._origin = update.message.text.upper()
            update.message.reply_text(TEXTS["SELECT_DESTINATION_STATION"],
                                      reply_markup=ReplyKeyboardMarkup(KEYBOARDS["STATIONS"], one_time_keyboard=True))
            return ConvStates.STATION
        else:
            logger.debug("Destination Station")
            self._conversations[userid]._dest = update.message.text.upper()
            bot.send_message(chat_id=userid,
                             text=TEXTS["SELECTED_TRIP"].format(
                                 origin=self._conversations[userid]._origin,
                                 destination=self._conversations[userid]._dest
                             ),
                             reply_markup=ReplyKeyboardRemove())
            bot.send_message(chat_id=userid, text=TEXTS["SELECT_TRIP_DATE"],
                             reply_markup=telegramcalendar.create_calendar())
            return ConvStates.DATE

    def _h_option(self, bot, update):
        userid = update.message.from_user.id
        ret_code = 0
        if update.message.text == TEXTS["MAIN_OP_DO_QUERY"]:
            self._conversations[userid]._option = BotOptions.DO_QUERY
            update.message.reply_text(TEXTS["DO_ONETIME_QUERY"])
            update.message.reply_text(TEXTS["SELECT_ORIGIN_STATION"],
                                      reply_markup=ReplyKeyboardMarkup(KEYBOARDS["STATIONS"], one_time_keyboard=True))
            ret_code = ConvStates.STATION
        elif update.message.text == TEXTS["MAIN_OP_ADD_QUERY"]:
            self._conversations[userid]._option = BotOptions.ADD_QUERY
            update.message.reply_text(TEXTS["ADD_PERIODIC_QUERY"])
            update.message.reply_text(TEXTS["SELECT_ORIGIN_STATION"],
                                      reply_markup=ReplyKeyboardMarkup(KEYBOARDS["STATIONS"], one_time_keyboard=True))
            ret_code = ConvStates.STATION
        elif update.message.text == TEXTS["MAIN_OP_DEL_QUERY"]:
            self._conversations[userid]._option = BotOptions.DEL_QUERY
            ret_code = RenfeBot.XXX
        elif update.message.text == TEXTS["MAIN_OP_CHECK_QUERY"]:
            user_queries = self._DB.get_user_queries(userid)
            if len(user_queries) == 0:
                update.message.reply_text(TEXTS["NO_QUERIES_FOR_USERID"])
            else:
                update.message.reply_text(TEXTS["QUERIES_FOR_USERID"])   
                for q in user_queries:
                    update.message.reply_text(TEXTS["QUERY_IN_DB"].format(origin=q["origin"],
                        destination=q["destination"], date=self._DB.timestamp_to_date(q["date"])))
            update.message.reply_text(TEXTS["END_MESSAGE"],reply_markup=ReplyKeyboardRemove())
            ret_code = ConversationHandler.END

        else:
            update.message.reply_text(TEXTS["MAIN_OP_UNKNOWN"])
            ret_code = ConversationHandler.END
        return ret_code

    def _start_conv_for_user(self, userid):
        if userid not in self._conversations:
            self._conversations[userid] = RenfeBot.Conversation(userid)
        self._conversations[userid].reset()

    def _h_start(self, bot, update):
        ret_code = 0
        userid = update.message.from_user.id
        username = update.message.from_user.first_name
        if update.message.from_user.last_name is not None:
            username += " " + update.message.from_user.last_name
        auth = self._DB.get_user_auth(userid, username)
        if auth == 0:  # Not authorized
            logger.debug("NOT AUTHORIZED USER")
            update.message.reply_text(TEXTS["NOT_AUTH_REPLY"].format(username=username),
                                      reply_markup=ReplyKeyboardRemove())
            self._ask_admin_for_access(bot, userid, username)
            ret_code = ConversationHandler.END
        else:  # Authorized
            logger.debug("AUTHORIZED USER")
            self._start_conv_for_user(userid)
            update.message.reply_text(TEXTS["OPTION_SELECTION"],
                                      reply_markup=ReplyKeyboardMarkup(
                                          KEYBOARDS["MAIN_OPTIONS"]),
                                      one_time_keyboard=True)
            ret_code = ConvStates.OPTION
        return ret_code

    def _ask_admin_for_access(self, bot, userid, username):
        keyboard = [
            ["/admin ALLOW %d %s" % (userid, username)],
            ["/admin NOT_ALLOW %d %s" % (userid, username)]
        ]
        bot.send_message(chat_id=self._admin_id,
                         text=TEXTS["ADMIN_USER_REQ_ACCESS"].format(
                             username=username
                         ),
                         reply_markup=ReplyKeyboardMarkup(keyboard),
                         one_time_keyboard=True)

    def _h_admin_access(self, bot, update, args):
        logger.debug("user command message received")
        userid = update.message.from_user.id
        username = "User "

        def addifnotnone(x): return x + " " if x is not None else ""
        username += addifnotnone(update.message.from_user.first_name)
        username += addifnotnone(update.message.from_user.last_name)
        username += addifnotnone(update.message.from_user.username)
        msg = "Resp: "
        if userid == self._admin_id:
            if args[0] == "ALLOW":
                self._DB.update_user(int(args[1]), args[2], 1)
                msg += "%s ALLOWED access" % (username)
            elif args[0] == "NOTALLOW":
                self._DB.update_user(int(args[1]), args[2], 0)
                msg += "%s NOT ALLOWED access" % (username)
            elif args[0] == "DB":
                logger.debug("Getting all notifications")
                self.send_db_to_admin(bot)
                msg += "Obtained all data."
            else:
                log.error("WTF!!!")
            bot.send_message(chat_id=userid, text=msg,
                             reply_markup=ReplyKeyboardRemove())
        else:
            bot.send_message(chat_id=userid,
                             text="Received unauthorized message: %s from %d-%s" %
                             (update.message.text,
                              userid,
                              username),
                             reply_markup=ReplyKeyboardRemove())

    def send_db_to_admin(self, bot):
        usersDF = self._DB.get_users_DF()
        queriesDF = self._DB.get_queries_DF()
        bot.send_message(chat_id=self._admin_id, text="Not ready yet!")

    def _install_handlers(self):
        self._conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self._h_start)],
            states={
                ConvStates.OPTION: [MessageHandler(Filters.text, self._h_option)],
                ConvStates.STATION: [MessageHandler(Filters.text, self._h_station)],
                ConvStates.DATE: [CallbackQueryHandler(self._h_date)]
            },
            fallbacks=[CommandHandler('cancel', self._h_cancel)]
        )
        self._updater.dispatcher.add_handler(self._conv_handler)
        self._updater.dispatcher.add_handler(CommandHandler("admin",
                                                            self._h_admin_access,
                                                            pass_args=True))

    def start(self):
        self._updater.start_polling()

    def stop(self):
        self._RF.close()
        self._updater.stop()

    def idle(self):
        self._updater.idle()


if __name__ == "__main__":
    rb = RenfeBot(TOKEN, ADMIN_ID)
    rb.start()
    rb.idle()
