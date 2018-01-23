#!/usr/local/bin/python3

from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler,
                          Filters, RegexHandler, ConversationHandler)
from telegram.ext import CallbackQueryHandler
from telegram.parsemode import ParseMode

import datetime
from enum import Enum
import logging



import renfechecker
import dbmanager as renfebotdb
from texts import texts as TEXTS
from texts import keyboards as KEYBOARDS
from bot_data import TOKEN, ADMIN_ID
from conversations import ConvStates, RenfeBotConversations

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)

logger = logging.getLogger(__name__)








class RenfeBot:
    def __init__(self, token, admin_id):
        self._token = token
        self._admin_id = admin_id
        self._updater = Updater(token)
        self._jobQ = self._updater.job_queue
        self._jobs = []
        self._CV = RenfeBotConversations()
        self._RF = renfechecker.RenfeChecker()
        self._DB = renfebotdb.RenfeBotDB("midatabase.db")
        self._install_handlers()

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
                ConvStates.DATE: [CallbackQueryHandler(self._h_date)],
                ConvStates.NUMERIC_OPTION: [CallbackQueryHandler(self._h_numeric_option)]
            },
            fallbacks=[CommandHandler('cancel', self._h_cancel)]
        )
        self._updater.dispatcher.add_handler(self._conv_handler)
        self._updater.dispatcher.add_handler(CommandHandler("admin",
                                                            self._h_admin_access,
                                                            pass_args=True))

    def check_periodic_queries(self):
        print("Checking")


    def register_jobs(self):
        j_morning = self._jobQ.run_daily(self.check_periodic_queries,
                                    time=datetime.time(8,30),
                                    days=(0,1,2,3,4,5,6),
                                    name="periodic0830")
        self._jobs.append(j_morning)
        j_afternoon = self._jobQ.run_daily(self.check_periodic_queries,
                                    time=datetime.time(16,0),
                                    days=(0,1,2,3,4,5,6),
                                    name="periodic1600")
        self._jobs.append(j_afternoon)
        j_mock_job = self._jobQ.run_repeating(self.check_periodic_queries,
                                            interval=60,
                                            name="periodicmock")
        self._jobs.append(j_mock_job)

    def start(self):
        self.register_jobs()
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
