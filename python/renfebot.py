#!/usr/local/bin/python3
"""
@author gonzalo-rodriguez
"""
#import telegram modules
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler,
                          Filters, RegexHandler, ConversationHandler)
from telegram.ext import CallbackQueryHandler
from telegram.parsemode import ParseMode

#import general modules
import datetime
from enum import Enum
import logging


# import my modules
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
    '''
    Main class of the bot. 
    Contains all other objects. 
    '''
    def __init__(self, token, admin_id):
        self._token = token
        self._admin_id = admin_id
        self._updater = Updater(token)
        self._jobQ = self._updater.job_queue
        #Conversions with the bot
        self._CV = RenfeBotConversations(self)
        #Checker in selenium
        self._RF = renfechecker.RenfeChecker()
        #DataBase
        self._DB = renfebotdb.RenfeBotDB("midatabase.db")
        #After everything is created install all telegram handlers. 
        self._install_handlers()

    def send_query_results_to_user(self, bot, userid, results, origin, dest, date):
        if results[0]:
            logger.debug("Returning data to user")
            trayectos = results[1]
            trenes = df.loc[df["DISPONIBLE"] == True]
            logger.debug("Obtained trenes")
            bot.send_message(chat_id=userid, text=TEXTS["FOUND_N_TRAINS"].
                             format(ntrains=trenes.shape[0], origin=origin, destination=dest, date=date))
            msg = ""
            for index, train in trenes.iterrows():
                msg += TEXTS["TRAIN_INFO"].format(
                                     t_departure=train.SALIDA.strftime(
                                         "%H:%M"),
                                     t_arrival=train.LLEGADA.strftime("%H:%M"),
                                     cost=train.PRECIO if train.PRECIO > 50 else "*" +
                                     str(train.PRECIO) + "*",
                                     ticket_type=train.TARIFA
                                 )
                msg += "\n"
            if msg != "":
                bot.send_message(chat_id=userid,
                                 text=msg,
                                 parse_mode=ParseMode.MARKDOWN)
        else:
            bot.send_message(chat_id=userid, text=TEXTS["NO_TRAINS_FOUND"].format(
                origin=origin, destination=dest, date=date))

  

    def ask_admin_for_access(self, bot, userid, username):
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
        #Create conv handler
        #The entry point should be something else than a /start command.
        self._conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self._CV.handler_start)],
            states={
                ConvStates.OPTION: [MessageHandler(Filters.text, self._CV.handler_option)],
                ConvStates.STATION: [MessageHandler(Filters.text, self._CV.handler_station)],
                ConvStates.DATE: [CallbackQueryHandler(self._CV.handler_date)],
                ConvStates.NUMERIC_OPTION: [CallbackQueryHandler(self._CV.handler_numeric_option)]
            },
            fallbacks=[CommandHandler('cancel', self._CV.handler_cancel)]
        )
        #Add conv handler
        self._updater.dispatcher.add_handler(self._conv_handler)
        #Add admin handler
        self._updater.dispatcher.add_handler(CommandHandler("admin",
                                                            self._h_admin_access,
                                                            pass_args=True))

    def check_periodic_queries(self, bot, job):
        bot.send_message(chat_id=self._admin_id,text="ADMIN: Checking periodic queries: "+job.name)
        queries = self._DB.get_queries()
        for q in queries:
            date = self._DB.timestamp_to_date(q["date"])
            res = self._RF.check_trip(q["origin"], q["destination"], date)
            self.send_query_results_to_user(bot, q["userid"], res,
                                                 q["origin"], q["destination"], date)

       
    def remove_old_periodic_queries(self, bot, job): 
        bot.send_message(chat_id=self._admin_id,text="ADMIN: Removing old queries: "+job.name)
        self._DB.remove_old_periodic_queries()

    def register_jobs(self):
        self._jobQ.run_daily(self.remove_old_periodic_queries,
                                    time=datetime.time(0, 0),
                                    days=(0, 1, 2, 3, 4, 5, 6),
                                    name="remove0800")
        self._jobQ.run_daily(self.check_periodic_queries,
                                    time=datetime.time(8, 30),
                                    days=(0, 1, 2, 3, 4, 5, 6),
                                    name="check0830")
        self._jobQ.run_daily(self.check_periodic_queries,
                                    time=datetime.time(16, 0),
                                    days=(0, 1, 2, 3, 4, 5, 6),
                                    name="check1600")
        self._jobQ.run_repeating(self.check_periodic_queries,
                                            interval=120,
                                            name="periodicmock")
        self._jobQ.run_repeating(self.remove_old_periodic_queries,
                                            interval=120,
                                            name="periodicmock2")
        
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
