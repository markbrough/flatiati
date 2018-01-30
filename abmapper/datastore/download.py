#!/usr/bin/env python

from lxml import etree
import urllib2
import os, datetime
from abmapper import app, db
from abmapper.query import models
from abmapper.query import projects
from abmapper.query import settings
import parse
import unicodecsv

URL = "http://datastore.iatistandard.org/api/1/access/activity.xml?reporting-org={}&recipient-country={}&stream=True"
URL_COUNTRY = "http://datastore.iatistandard.org/api/1/access/activity.xml?reporting-org={}&recipient-country={}&stream=True"
IDENTIFIER_URL = "http://datastore.iatistandard.org/api/1/access/activity.xml?iati-identifier={}&stream=True"

basedir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.path.pardir))

def download_data(reporting_org, country_code=None,
                    update_exchange_rates=False, save=False):
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

    def get_doc(the_url):
        print "Fetching data from {}".format(the_url)
        xml_data = urllib2.urlopen(the_url, timeout=60).read()
        return etree.fromstring(xml_data)

    if country_code:
        doc = get_doc(URL_COUNTRY.format(reporting_org, country_code))
    else:
        active_countries = projects.countries_active()
        country_codes = "|".join(active_countries)
        doc = get_doc(URL.format(reporting_org, country_codes))

    # Check if complete for hierarchies
    iati_identifiers = doc.xpath("//iati-identifier/text()")
    related_activity_identifiers = doc.xpath("//related-activity[@type='1' or @type='2']/@ref")
    def filter_related_doesnt_exist(related_identifier):
        return related_identifier not in iati_identifiers
    unfound_identifiers = set(filter(filter_related_doesnt_exist, related_activity_identifiers))

    if len(unfound_identifiers)>0:
        ufdoc = get_doc(IDENTIFIER_URL.format("|".join(unfound_identifiers)))
        ufdoc_activities = ufdoc.xpath("//iati-activity")
        doc_iati_activities = doc.find("iati-activities")
        for ufdoc_activity in ufdoc_activities:
            doc_iati_activities.append(ufdoc_activity)

    if reporting_org=="US-GOV-1":
        """We do some clean up for USAID activities"""
        print("There are {} activities", 
            len(doc.xpath("//iati-activity")))
        # We clean up data for now
        codelists_dir = os.path.join(basedir, 
            "lib", "codelists", "donors")
        usaid_csv_f = open(os.path.join(codelists_dir, 
            "USAID SPSD Areas and Elements 2017-08-31.csv"), "r")
        usaid_csv = unicodecsv.DictReader(usaid_csv_f)
        prohibited_names = list(map(lambda x: x["name"], usaid_csv))
        doc_activities = doc.xpath("//iati-activity")
        for activity in doc_activities:
            if activity.find("title").find("narrative").text in prohibited_names:
                activity.getparent().remove(activity) 
        print("There are {} activities", 
            len(doc.xpath("//iati-activity")))
    if not save:
        parse.parse_doc(reporting_org_id, doc, update_exchange_rates)
    else:
        write_data(doc)
