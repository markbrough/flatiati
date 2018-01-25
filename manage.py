#!/usr/bin/env python
# -*- coding: utf-8 -*-

#  Flat IATI, generate spreadsheets from IATI data
#
#  Copyright (C) 2013  Publish What You Fund
#  Copyright (C) 2017  Mark Brough, Overseas Development Institute
#
#  This programme is free software; you may redistribute and/or modify
#  it under the terms of the GNU Affero General Public License v3.0

from flask.ext.script import Manager, Command
from flask_frozen import Freezer
import abmapper
from abmapper import app

app.config['FREEZER_IGNORE_ENDPOINTS'] = ['admin', 'api_reporting_orgs']

def no_argument_rules_urls_with_ignore():
    """URL generator for URL rules that take no arguments."""
    ignored = app.config.get('FREEZER_IGNORE_ENDPOINTS', [])
    for rule in app.url_map.iter_rules():
        if rule.endpoint not in ignored and not rule.arguments and 'GET' in rule.methods:
            yield rule.endpoint, {}

freezer = Freezer(app=app, with_no_argument_rules=False)
freezer.register_generator(no_argument_rules_urls_with_ignore)

class Freeze(Command):
    "Freezes site and spreadsheets"
    
    def run(self):
        app.config["FREEZE"] = True

        print ""
        print "Freezing site"
        freezer.freeze()

def run():
    manager = Manager(app)
    manager.add_command('freeze', Freeze())
    manager.run()

if __name__ == "__main__":
    run()
