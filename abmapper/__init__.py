# -*- coding: utf-8 -*-

from flask import Flask, request, session, redirect, url_for, flash
from flask.ext.babel import Babel
from flask.ext.sqlalchemy import SQLAlchemy
from urlparse import urlparse, urljoin
import os
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlite3 import Connection as SQLite3Connection

@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

app = Flask(__name__.split('.')[0])
app.config.from_pyfile(os.path.join('..', 'config.py'))
db = SQLAlchemy(app)
babel = Babel(app)

from abmapper.query import models
import routes

LANGUAGES = app.config["LANGUAGES"].keys()

@babel.localeselector
def get_locale():
    if 'lang' in session:
        return session['lang']
    # try to guess the language from the user accept
    # header the browser transmits. The best match wins.
    return request.accept_languages.best_match(LANGUAGES)

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc

def get_redirect_target():
    if request.referrer and is_safe_url(request.referrer):
        return request.referrer
    return url_for("dashboard")

@app.route("/lang/<lang>/")
def set_lang(lang):
    print LANGUAGES
    if lang in LANGUAGES:
        session['lang'] = lang
        return redirect(get_redirect_target())
    else:
        flash("Unrecognised language", "error")
        return redirect(get_redirect_target())