from abmapper import db, models
import unicodecsv
import os
import urllib2
import json

CODELISTS_API = "http://iatistandard.org/codelists/downloads/clv2/json/en/%s.json"

def setup():
    db.create_all()
    import_common_code()
    import_sectors()
    import_activity_statuses()
    import_aid_types()

def import_common_code():
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib/common_code.csv'), 'r') as csvfile:
        ccreader = unicodecsv.DictReader(csvfile)
        for row in ccreader:
            cc = models.CommonCode()
            cc.id = row["CC code"]
            cc.category = row["Category of Government"]
            cc.sector = row["Sector"]
            cc.function = row["Function"]
            db.session.add(cc)
        db.session.commit()

def import_sectors():
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib/crs_cc.csv'), 'r') as csvfile:
        crsccreader = unicodecsv.DictReader(csvfile)
        for row in crsccreader:
            crscc = models.DACSector()
            crscc.code = row["CRS_code"]
            crscc.dac_sector_code = row["DAC_sector_code"]
            crscc.dac_sector_name = row["DAC_sector_name"]
            crscc.dac_five_code = row["DAC_5_code"]
            crscc.dac_five_name = row["DAC_5_name"]
            crscc.description = row["DESCRIPTION"]
            crscc.notes = row["notes"]
            crscc.parent_code = row["parent_code"]
            crscc.cc_id = row["cc_id"]
            db.session.add(crscc)
        db.session.commit()

def import_activity_statuses():
    statuses = {
        1: "Pipeline/identification",
        2: "Implementation",
        3: "Completion",
        4: "Post-completion",
        5: "Cancelled",
    }
    for code, text in statuses.items():
        activitystatus = models.ActivityStatus()
        activitystatus.code = code
        activitystatus.text = text
        db.session.add(activitystatus)
    db.session.commit()

def import_aid_types():
    aid_type_url = CODELISTS_API % 'AidType'
    sourcedata = urllib2.urlopen(aid_type_url, timeout=60).read()
    data = json.loads(sourcedata)['data']
    for code in data:
        nc = models.AidType()
        nc.code = code['code']
        nc.text = code['name']
        db.session.add(nc)
    db.session.commit()
