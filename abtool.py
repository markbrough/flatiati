#!/usr/bin/env python

import optparse, sys
from abmapper import projects

def update_projects(options):
    print options
    assert options.filename
    assert options.reporting_org
    assert options.country_code
    projects.update_project(options)

commands = {
    "update_projects": (update_projects, "Update projects"),
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
