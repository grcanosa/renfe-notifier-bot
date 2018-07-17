"""

"""
from enum import Enum
import logging

from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import ConversationHandler

from telegramcalendarkeyboard import telegramcalendar
from telegramcalendarkeyboard import telegramoptions

from texts import texts as TEXTS
from texts import keyboards as KEYBOARDS


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)


class BotOptions(Enum):
    ADD_QUERY = 1
    DEL_QUERY = 2
    DO_QUERY = 3


class ConvStates(Enum):
    OPTION = 1
    STATION = 2
    DATE = 3
    NUMERIC_OPTION = 4


class RenfeBotConversations:
    class Conversation:
        def __init__(self, userid):
            self._userid = userid
            self.reset()

        def reset(self):
            self._option = 0
            self._origin = None
            self._dest = None
            self._date = None
            self._data = None

    def __init__(self, renfebot):
        self._conversations = {}
        self._RB = renfebot

    def _start_conv_for_user(self, userid):
        if userid not in self._conversations:
            self._conversations[userid] = self.Conversation(userid)
        self._conversations[userid].reset()

    def handler_start(self, bot, update):
        ret_code = 0
        userid = update.message.from_user.id
        username = update.message.from_user.first_name
        if update.message.from_user.last_name is not None:
            username += " " + update.message.from_user.last_name
        auth = self._RB._DB.get_user_auth(userid, username)
        if auth == 0:  # Not authorized
            logger.debug("NOT AUTHORIZED USER")
            update.message.reply_text(TEXTS["NOT_AUTH_REPLY"].format(username=username),
                                      reply_markup=ReplyKeyboardRemove())
            self._RB.ask_admin_for_access(bot, userid, username)
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

    def handler_cancel(self, bot, update):
        return ConversationHandler.END

    def handler_option(self, bot, update):
        userid = update.message.from_user.id
        ret_code = 0
        if update.message.text == TEXTS["MAIN_OP_DO_QUERY"]:
            ret_code = self._h_op_do_query(userid, bot, update)
        elif update.message.text == TEXTS["MAIN_OP_ADD_QUERY"]:
            ret_code = self._h_op_add_query(userid, bot, update)
        elif update.message.text == TEXTS["MAIN_OP_DEL_QUERY"]:
            ret_code = self._h_op_del_query(userid, bot, update)
        elif update.message.text == TEXTS["MAIN_OP_CHECK_QUERY"]:
            ret_code = self._h_op_check_queries(userid, bot, update)
        else:
            update.message.reply_text(TEXTS["MAIN_OP_UNKNOWN"])
            ret_code = ConversationHandler.END
        return ret_code

    def _h_op_do_query(self, userid, bot, update):
        self._conversations[userid]._option = BotOptions.DO_QUERY
        update.message.reply_text(TEXTS["DO_ONETIME_QUERY"])
        update.message.reply_text(TEXTS["SELECT_ORIGIN_STATION"],
                                    reply_markup=ReplyKeyboardMarkup(KEYBOARDS["STATIONS"],
                                    one_time_keyboard=True))
        return ConvStates.STATION

    def _h_op_add_query(self, userid, bot, update):
        self._conversations[userid]._option = BotOptions.ADD_QUERY
        update.message.reply_text(TEXTS["ADD_PERIODIC_QUERY"])
        update.message.reply_text(TEXTS["SELECT_ORIGIN_STATION"],
                                    reply_markup=ReplyKeyboardMarkup(KEYBOARDS["STATIONS"],
                                    one_time_keyboard=True))
        return ConvStates.STATION

    def _h_op_del_query(self, userid, bot, update):
        self._conversations[userid]._option = BotOptions.DEL_QUERY
        user_queries = self._RB._DB.get_user_queries(userid)
        ret_code = 0
        if len(user_queries) == 0:
            update.message.reply_text(TEXTS["NO_QUERIES_FOR_USERID"])
            ret_code = ConversationHandler.END
        else:
            options = []
            for q in user_queries:
                options.append(TEXTS["QUERY_IN_DB"].
                                    format(origin=q["origin"],
                                           destination=q["destination"],
                                           date=self._RB._DB.timestamp_to_date(q["date"])))
            bot.send_message(chat_id=userid,
                            text=TEXTS["SELECT_TRIP_TO_DETELE"],
                            reply_markup=telegramoptions.create_options_keyboard(options,TEXTS["CANCEL"]))
            self._conversations[userid]._data = user_queries
            ret_code = ConvStates.NUMERIC_OPTION
        return ret_code


    def _h_op_check_queries(self, userid, bot, update):
        user_queries = self._RB._DB.get_user_queries(userid)
        if len(user_queries) == 0:
            update.message.reply_text(TEXTS["NO_QUERIES_FOR_USERID"])
        else:
            update.message.reply_text(TEXTS["QUERIES_FOR_USERID"])   
            for q in user_queries:
                update.message.reply_text(TEXTS["QUERY_IN_DB"].
                                format(origin=q["origin"],
                                destination=q["destination"],
                                date=self._RB._DB.timestamp_to_date(q["date"])))
        update.message.reply_text(TEXTS["END_MESSAGE"],reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    def handler_numeric_option(self, bot, update):
        logger.debug("Processing numeric opion")
        userid = update.callback_query.from_user.id
        user_queries = self._conversations[userid]._data
        selected, query_index = telegramoptions.process_option_selection(bot, update)
        if not selected:
            logger.debug("Nothing selected")
            bot.send_message(chat_id= userid, text=TEXTS["DB_QUERY_NOT_REMOVED"],reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
        else:
            logger.debug("Deleting query with index "+str(query_index))
            if len(user_queries) > query_index:
                query = user_queries[query_index]
                if self._RB._DB.remove_periodic_query(query["userid"], query["origin"],
                                     query["destination"], query["date"]):
                    bot.send_message(chat_id=userid,text=TEXTS["DB_QUERY_REMOVED"],reply_markup=ReplyKeyboardRemove())
                else:
                    bot.send_message(chat_id=userid,text=TEXTS["DB_QUERY_NOT_PRESENT"],reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    def handler_date(self, bot, update):
        logger.debug("Processing date")
        selected, date = telegramcalendar.process_calendar_selection(bot, update)
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
                res = self._RB._DB.add_periodic_query(
                    userid, conv._origin, conv._dest, conv._date)
                bot.send_message(chat_id=userid,text=res[1])
            elif conv._option == BotOptions.DO_QUERY:
                bot.send_message(chat_id=userid,text=TEXTS["WAIT_FOR_TRAINS"])
                res = self._RB._RF.check_trip(conv._origin, conv._dest, conv._date)
                self._RB.send_query_results_to_user(bot, userid, res,
                                                 conv._origin, conv._dest, conv._date)
            else:
                logger.error("Problem, no other option should lead HERE!")
        return ConversationHandler.END  


    def handler_station(self, bot, update):
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