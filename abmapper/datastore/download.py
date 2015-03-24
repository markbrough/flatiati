#!/usr/bin/env python

from lxml import etree
import urllib2
import os, datetime
from abmapper import app, db
from abmapper.query import models
from abmapper.query import projects

URL = "http://iati-datastore.herokuapp.com/api/1/access/activity.xml?recipient-country=%s&reporting-org=%s&stream=True"

def download_data(country, reporting_org):
    def write_data(doc):
        LOCAL_DIR=app.config["DATA_STORAGE_DIR"]
        path = os.path.join(LOCAL_DIR, "iati_data_" + country + '.xml')
        iati_activities = etree.tostring(doc.find("iati-activities"))
        with file(path, 'w') as localFile:
            localFile.write(iati_activities)

    the_url = URL % (country, reporting_org)
    print the_url

    xml_data = urllib2.urlopen(the_url, timeout=60).read()
    doc = etree.fromstring(xml_data)
    write_data(doc)