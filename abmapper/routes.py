# -*- coding: utf-8 -*-
from abmapper import app
import setup as absetup
from views import export, projects, dashboard

@app.route("/setup/")
def setup():
    absetup.setup()
    return "OK"