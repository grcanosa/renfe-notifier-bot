#!/usr/bin/python3


import os
import pandas as pd
import sqlite3
import datetime


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class RenfeBotDB:
    def __init__(self,f_database):
        self._f_database = f_database
        self._create_db_if_necessary()

    def _openclose(foo):
        def wrapper(self,*args, **kw):
            conn = sqlite3.connect(self._f_database)
            conn.row_factory = dict_factory
            cur = conn.cursor()
            ret = foo(self,conn,cur,*args, **kw)
            cur.close()
            conn.close()
            return ret
        return wrapper

    def _create_db_if_necessary(self):
        if not os.path.isfile(self._f_database):
            #create DB
            conn = sqlite3.connect(self._f_database)
            cur = conn.cursor()
            cur.execute("""CREATE TABLE users (userid INTEGER PRIMARY KEY,
                                                username TEXT,
                                                auth INTEGER)""")
            cur.execute("""CREATE TABLE queries (origin TEXT,
                                                    destination TEXT,
                                                    date INTEGER,
                                                    userid INTEGER,
                                                    FOREIGN KEY(userid) REFERENCES users(userid))""")
            conn.commit()
            cur.close()
            conn.close()

    @_openclose
    def get_user_auth(self,conn,cur,userid,username):
        auth = 0
        cur.execute("SELECT auth FROM users WHERE userid=%d" %(userid))
        val = cur.fetchall()
        if len(val) == 0:
            cur.execute("INSERT INTO users VALUES (%d,\"%s\",%d);"%(userid,username,0))
            conn.commit()
        elif len(val) == 1: #User found
            auth = val[0]["auth"]
        else:
            logger.error("Not possible, something is clearly wrong")
        return auth

    @_openclose
    def update_user(self,conn,cur,userid,username,auth):
        cur.execute("UPDATE users SET username=\"%s\", auth=%d WHERE userid=%d" %
                        (username,auth,userid))
        conn.commit()

    def date_to_timestamp(date):
        return int(datetime.datetime.strptime(date,"%d/%m/%Y").timestamp())

    def get_user_queries(self,cur,userid):
        cur.execute("SELECT * FROM queries WHERE userid=%d" % (userid))
        return cur.fetchall()

    @_openclose
    def add_periodic_query(self,conn,cur,userid,origin,destination,date):
        i_date = self.date_to_timestamp(date)
        #user_queries =

    @_openclose
    def remove_periodic_query(self,conn,cur,userid,origin,destination,date):
        print("lala")

    @_openclose
    def _add_notification(self,conn,cur,userid,origin,destination,date):
        #Convert date from string to number
        i_date = self.date_to_timestamp(date)
        cur.execute("INSERT INTO notifications VALUES(%s,%s,%d,%d);" %
            (origin,destination,i_date,userid))
        conn.commit()

    @_openclose
    def _remove_notification(self,conn,cur,userid,origin,destination,date):
        i_date = int(datetime.datetime.strptime(date,"%d/%m/%Y").timestamp())
        cur.execute("DELETE FROM notifications WHERE origin=%s "+
                                                "AND destination=%s "+
                                                "AND date=%d "+
                                                "AND userid=%d;" %
            (origin,destination,i_date,userid))
        conn.commit()


  #   def _check_trains(self):
  #
  #
  #   def get_unique_trips(DF):
  #
  #       SELECT DISTINCT Latitude, Longitude
  # FROM Coordinates
  #
  #       return DF.groupby(["ORIGIN","DESTINATION","DATE"])["USER_ID"].index
