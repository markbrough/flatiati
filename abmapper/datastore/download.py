#!/usr/bin/env python

from lxml import etree
import urllib2
import os, datetime
from abmapper import app, db
from abmapper.query import models
from abmapper.query import projects
from abmapper.query import settings
import parse

URL = "http://datastore.iatistandard.org/api/1/access/activity.xml?recipient-country={}&reporting-org={}&stream=True"

def download_data(country_code, reporting_org, update_exchange_rates=False, save=False):
    # Check if reporting org exists
    reporting_org_obj = settings.reporting_org_by_code(reporting_org)
    if reporting_org_obj:
        reporting_org_id = reporting_org_obj.id
    else:
        reporting_org_id = settings.add_reporting_org(reporting_org)
    def write_data(doc):
        LOCAL_DIR=app.config["DATA_STORAGE_DIR"]
        path = os.path.join(LOCAL_DIR, "iati_data_" + country_code + '.xml')
        iati_activities = etree.tostring(doc.find("iati-activities"))
        with file(path, 'w') as localFile:
            localFile.write(iati_activities)

    the_url = URL.format(country_code, reporting_org)
    print "Fetching data from {}".format(the_url)
    xml_data = urllib2.urlopen(the_url, timeout=60).read()
    doc = etree.fromstring(xml_data) #.xpath("//iati-activities")
    if not save:
        parse.parse_doc(country_code, reporting_org_id, doc, update_exchange_rates)
    else:
        write_data(doc)
