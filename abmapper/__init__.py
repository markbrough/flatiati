# -*- coding: utf-8 -*-

from flask import Flask, request, session, redirect, url_for, flash
from flask.ext.babel import Babel
from flask.ext.sqlalchemy import SQLAlchemy
import os

app = Flask(__name__.split('.')[0])
app.config.from_pyfile(os.path.join('..', 'config.py'))
db = SQLAlchemy(app)
babel = Babel(app)

import routes

LANGUAGES = app.config["LANGUAGES"].keys()

@babel.localeselector
def get_locale():
    if 'lang' in session:
        return session['lang']
    # try to guess the language from the user accept
    # header the browser transmits. The best match wins.
    return request.accept_languages.best_match(LANGUAGES)

@app.route("/lang/<lang>/")
def set_lang(lang):
    print LANGUAGES
    if lang in LANGUAGES:
        session['lang'] = lang
        return redirect(url_for('dashboard'))
    else:
        flash("Unrecognised language", "error")
        return redirect(url_for('dashboard'))