#!/usr/bin/env python

# Takes IATI-XML with hierarchy, finds lowest hierarchy for each reporting-org
# and returns IATI-XML data with higher-level activity data mapped onto the
# lowest level.

import optparse, sys
from lxml import etree
import urllib2
import os, datetime

URL = "http://iati-datastore.herokuapp.com/api/1/access/activity.xml?recipient-country=%s&reporting-org=CA-3&stream=True"

"""
  Get set of reporting-org/@ref's
  For each each reporting-org/@ref:
    Get all activities belonging to it, stick them in:
    data = {
       '41114': {
            '1': {
                '41114-PROJECT-00047260': etree_object,
            },
            '2' : {
                '41114-OUTPUT-00052143': etree_object,
            },
        }
    }
    Get highest value in data, set that as the flattee
    For each of those, find parent and flatten onto flattee
    
"""

def get_iati_activities(doc):
    import copy
    newdoc = copy.deepcopy(doc)
    root = newdoc.getroot()
    for e in root:
        root.remove(e)
    return root

def get_reporting_org_activities(rep, iati_activities, doc):
    data = {}
    out_data = iati_activities

    # NB this won't return activities without a hierarchy
    
    hierarchies = set(doc.xpath(('//iati-activity[reporting-org/@ref="%s"]/@hierarchy' % (rep))))
    for h in hierarchies:
        data[h] = {}
        rep_h_acts = doc.xpath(('//iati-activity[reporting-org/@ref="%s"][@hierarchy="%s"]' % (rep, h)))
        for a in rep_h_acts:
            data[h][a.find('iati-identifier').text] = a

    # Get highest hierarchy
    max_hierarchy = max(hierarchies)
    for iati_id, activity in data[max_hierarchy].items():

        activity.attrib.pop("hierarchy")
        
        # Get h-1 activity
        parent_iati_id = activity.xpath('related-activity[@type="1"]/@ref')[0]
        parent_activity = data[str(int(max_hierarchy)-1)][parent_iati_id]
        
        for element in parent_activity:
            # Add information to the child
            activity.append(element)

        out_data.append(activity)
    return rep, out_data

def generate_flattened_xml(filename):
    doc = etree.parse(filename)
    iati_activities = get_iati_activities(doc)
    reporting_orgs = set(doc.xpath('//reporting-org/@ref'))

    return dict([get_reporting_org_activities(rep, 
                                              iati_activities, 
                                              doc
                    ) for rep in reporting_orgs])

def flatten(options):
    assert options.input
    assert options.output
    out_data = generate_flattened_xml(options.input)
    print "Generating flattened XML"

    for reporting_org, data in out_data.items():
        doc = etree.ElementTree(data)
        reporting_org_fn = "%s-out.xml" % reporting_org
        doc.write(os.path.join(options.output, reporting_org_fn),
        encoding='utf-8', xml_declaration=True, pretty_print=True)
        print "Written for reporting org %s" % (reporting_org)

commands = {
    "flatten": (flatten, "Flatten file, with in/out args"),
}

def main():
    p = optparse.OptionParser()

    for k, v in commands.iteritems():
        handler, help_text = v
        option_name = "--" + k.replace("_", "-")
        p.add_option(option_name, dest=k, action="store_true", default=False, help=help_text)

    p.add_option("--input", dest="input",
                 help="Set filename of data to import")
    p.add_option("--output", dest="output",
                 help="Set directory for output data")

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