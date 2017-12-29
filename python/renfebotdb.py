#!/usr/bin/python3


import os
import pandas as pd
import sqlite3
import datetime


from renfebottexts import texts as TEXTS

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
    def get_user_auth(self, conn, cur, userid, username):
        auth = 0
        cur.execute("SELECT auth FROM users WHERE userid=%d" % (userid))
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

    def date_to_timestamp(self, date):
        return int(datetime.datetime.strptime(date,"%d/%m/%Y").timestamp())

    def timestamp_to_date(self, timestamp):
        return datetime.datetime.fromtimestamp(timestamp).strftime("%d/%m/%Y")

    @_openclose
    def get_user_queries(self,conn,cur,userid):
        cur.execute("SELECT * FROM queries WHERE userid=%d" % (userid))
        return cur.fetchall()

    def _get_user_queries(self,cur,userid):
        cur.execute("SELECT * FROM queries WHERE userid=%d" % (userid))
        return cur.fetchall()

    @_openclose
    def add_periodic_query(self,conn,cur,userid,origin,destination,date):
        ret = (False, "")
        i_date = self.date_to_timestamp(date)
        user_queries = self._get_user_queries(cur,userid)
        found = False
        for q in user_queries:
            if q["origin"] == origin and q["destination"] == destination and q["date"] == i_date:
                logger.debug("Query already in DB")
                ret = (False,TEXTS["DB_QUERY_ALREADY"])
                found = True
                break
        if not found:
            cur.execute("INSERT INTO queries VALUES (\"%s\", \"%s\", %d, %d);" %
                (origin, destination, i_date, userid))
            conn.commit()
            ret = (True,TEXTS["DB_QUERY_INSERTED"])
        return ret

    @_openclose
    def remove_periodic_query(self,conn,cur,userid,origin,destination,date):
        ret = (False,"")
        i_date = self.datetime_to_timestamp(date)
        user_queries = self.get_user_queries(cur,userid)
        found = False
        for q in user_queries:
            if q["origin"] == origin and q["destination"] == destination and q["date"] == i_date:
                logger.debug("Query found")
                cur.execute("DELETE FROM queries WHERE origin=%s "+
                                                "AND destination=%s "+
                                                "AND date=%d "+
                                                "AND userid=%d;" %
                    (origin,destination,i_date,userid))
                conn.commit()
                ret = (True, TEXTS["DB_QUERY_REMOVED"])
                found = True
                break;
        if not found:
            ret = (False,TEXTS["DB_QUERY_NOT_PRESENT"])
        return ret

    @_openclose
    def get_distinct_queries(self,conn,cur):
        cur.execute("SELECT DISTINCT origin,destination,date FROM notifications;")
        return cur.fetchall()





  #   def _check_trains(self):
  #
  #
  #   def get_unique_trips(DF):
  #
  #       SELECT DISTINCT Latitude, Longitude
  # FROM Coordinates
  #
  #       return DF.groupby(["ORIGIN","DESTINATION","DATE"])["USER_ID"].index
