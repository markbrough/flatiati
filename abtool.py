#!/usr/bin/env python
# -*- coding: utf-8 -*-

import optparse, sys
from abmapper.query import projects as abprojects
from abmapper.query import update as abupdate
from abmapper.datastore import download, parse
from abmapper.query import setup as absetup
from abmapper.query import budget as abbudget
from abmapper.query import settings as absettings

def update_projects(options):
    print options
    assert options.filename
    assert options.reporting_org
    assert options.country_code
    abupdate.update_projects(options)

def import_budget(options):
    print options
    assert options.filename
    assert options.country_code
    assert options.budget_type
    abbudget.import_budget(options)

def import_iati_xml(options):
    print options
    assert options.filename
    assert options.country_code
    sample = bool(options.sample)
    parse.parse_file(options.country_code, options.filename, sample)

def download_iati_xml(options):
    assert options.reporting_org
    sample = bool(options.sample)
    print ""
    print "Download and import data"
    print ""
    print """Downloading IATI XML for country {} and reporting organisation {}""".format(options.country_code, options.reporting_org)
    download.download_data(options.reporting_org, options.country_code or None)

def update_codelists(options):
    absetup.update_codelists()

def update_exchange_rates(options):
    print ""
    print "Updating exchange rates"
    absetup.update_exchange_rates()

def update_all_reporting_orgs(options):
    orgs = absettings.reporting_orgs()
    print ""
    print "Download and import data"
    for org in orgs:
        if org.active == True:
            print ""
            print """Downloading IATI XML for reporting organisation {}""".format(org.text_EN)
            download.download_data(org.code)

def remake(options):
    absetup.trash()
    absetup.setup()
    if options.rates:
        absetup.update_exchange_rates()

def setup(options):
    absetup.setup()

commands = {
    "setup": (setup, "Setup"),
    "import": (import_iati_xml, "Import IATI XML file"),
    "download": (download_iati_xml, "Download and Import IATI XML file"),
    "update-projects": (update_projects, "Update projects"),
    "import-budget": (import_budget, "Import CC-budget mapping"),
    "remake": (remake, "Trash the database and regenerate"),
    "update-codelists": (update_codelists, "Update cached codelists"),
    "update-exchange-rates": (update_exchange_rates, "Update exchange rates"),
    "update-all": (update_all_reporting_orgs, "Update all reporting orgs"),
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
    p.add_option("--sample", dest="sample", action="store_true",
                 help="Only import a sample of 50 activities")
    p.add_option("--rates", dest="rates", action="store_true",
                 help="With remake, update exchange rates")

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
