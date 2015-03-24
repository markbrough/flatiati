#!/usr/bin/env python
# -*- coding: utf-8 -*-

import optparse, sys
from abmapper.query import projects as abprojects
from abmapper.datastore import download, parse
from abmapper.query import setup as absetup

def update_projects(options):
    print options
    assert options.filename
    assert options.reporting_org
    assert options.country_code
    abprojects.update_project(options)

def import_budget(options):
    print options
    assert options.filename
    assert options.country_code
    assert options.budget_type
    abprojects.import_budget(options)

def import_iati_xml(options):
    print options
    assert options.filename
    assert options.country_code
    parse.parse_file(options.country_code, options.filename)

def setup(options):
    absetup.setup()

commands = {
    "quicksetup": (setup, "Quick Setup with default arguments"),
    "setup": (setup, "Setup"),
    "import": (import_iati_xml, "Import IATI XML file"),
    "update-projects": (update_projects, "Update projects"),
    "import-budget": (import_budget, "Import CC-budget mapping"),
}

def main():
    p = optparse.OptionParser()

    for k, v in commands.iteritems():
        handler, help_text = v
        option_name = "--" + k.replace("_", "-")
        p.add_option(option_name, dest=k, action="store_true", default=False, help=help_text)
    
    p.add_option("--reporting-org", dest="reporting_org",
                 help="Set reporting org for projects to update")
    p.add_option("--country-code", dest="country_code",
                 help="Set country code for projects to update")
    p.add_option("--filename", dest="filename",
                 help="Set filename of data to update")
    p.add_option("--lang", dest="lang",
                 help="Set language for setup")
    p.add_option("--budget-type", dest="budget_type",
                 help="Set type of budget for importing (a, f)")

    options, args = p.parse_args()

    for mode, handler_ in commands.iteritems():
        handler, _ = handler_
        if getattr(options, mode, None):
            handler(options)
            return
    
    usage()

def usage():
    print "You need to specify which mode to run under"
    sys.exit(1)

if __name__ == '__main__':
    main()
