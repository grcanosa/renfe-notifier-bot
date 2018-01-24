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
        def __init__(self, userid, renfeDB):
            self._userid = userid
            self._DB = renfeDB
            self.reset()

        def reset(self):
            self._option = 0
            self._origin = None
            self._dest = None
            self._date = None
            self._data = None

    def __init__(self,renfebot):
        self._conversations = {}
        self._RB = renfebot

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
        user_queries = self._DB.get_user_queries(userid)
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
                                           date=self._DB.timestamp_to_date(q["date"])))
            bot.send_message(chat_id=userid,
                            text=TEXTS["SELECT_TRIP_TO_DETELE"],
                            reply_markup=telegramoptions.create_options_keyboard(options))
            self._conversations[userid]._data = user_queries
            ret_code = ConvStates.NUMERIC_OPTION
        return ret_code


    def _h_option_check_queries(self, userid, bot, update):
        user_queries = self._DB.get_user_queries(userid)
        if len(user_queries) == 0:
            update.message.reply_text(TEXTS["NO_QUERIES_FOR_USERID"])
        else:
            update.message.reply_text(TEXTS["QUERIES_FOR_USERID"])   
            for q in user_queries:
                update.message.reply_text(TEXTS["QUERY_IN_DB"].
                                format(origin=q["origin"],
                                destination=q["destination"],
                                date=self._DB.timestamp_to_date(q["date"])))
        update.message.reply_text(TEXTS["END_MESSAGE"],reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    def _h_numeric_option(self,userid,bot,update):
        logger.debug("Processing numeric opion")
        selected, query_index = telegramoptions.process_option_selection(bot,update)


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
                res = self._RB._RF.check_trip(conv._origin, conv._dest, conv._date)
                self._send_query_results_to_user(bot, userid, res,
                                                 conv._origin, conv._dest, conv._date)
            else:
                logger.error("Problem, no other option should lead HERE!")
        return ConversationHandler.END  
