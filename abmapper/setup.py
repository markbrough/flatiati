from abmapper import db, models
import unicodecsv
import os
import urllib2
import json
from flask import abort

CODELISTS_API = "http://iatistandard.org/codelists/downloads/clv2/json/%s/%s.json"

def setup(lang="EN"):
    allowed_langs=["EN", "FR"]
    if lang not in allowed_langs:
        return abort(403)
    db.create_all()
    import_common_code(lang)
    import_sectors(lang)
    import_activity_statuses(lang)
    import_aid_types(lang)
    import_recipient_countries(lang)
    import_budget_types(lang)

def import_common_code(lang):
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib/CC_EN_FR.csv'), 'r') as csvfile:
        ccreader = unicodecsv.DictReader(csvfile)
        for row in ccreader:
            cc = models.CommonCode()
            cc.id = row["CC code"]
            if lang=="EN":
                cc.category = row["Category of Government"]
                cc.sector = row["Sector"]
                cc.function = row["Function"]
            elif lang=="FR":
                cc.category = row["Categorie de gouvernement"]
                cc.sector = row["Secteur"]
                cc.function = row["Fonction"]                
            db.session.add(cc)
        db.session.commit()

def import_sectors(lang):
    if lang=="EN":
        filename = "crs_cc_EN.csv"
    elif lang=="FR":
        filename = "crs_cc_FR.csv"
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib/'+filename), 'r') as csvfile:
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

def import_activity_statuses(lang):
    if lang=="EN":
        enfr="en"
    elif lang=="FR":
        enfr="fr"
    aid_type_url = CODELISTS_API % (enfr, 'ActivityStatus')
    sourcedata = urllib2.urlopen(aid_type_url, timeout=60).read()
    data = json.loads(sourcedata)['data']
    for code in data:
        activitystatus = models.ActivityStatus()
        activitystatus.code = code["code"]
        activitystatus.text = code["name"]
        db.session.add(activitystatus)
    db.session.commit()

def import_aid_types(lang): 
    filename="aid_type_EN_FR.csv"
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib/'+filename), 'r') as csvfile:
        aidtypereader = unicodecsv.DictReader(csvfile)
        for row in aidtypereader:
            nc = models.AidType()
            nc.code = row["Code"]
            nc.text = row[lang + "_Description"]
            db.session.add(nc)
    db.session.commit()

def import_recipient_countries(lang):
    # Only EN available via IATI API
    enfr="en"
    aid_type_url = CODELISTS_API % (enfr, 'Country')
    sourcedata = urllib2.urlopen(aid_type_url, timeout=60).read()
    data = json.loads(sourcedata)['data']
    for code in data:
        rc = models.RecipientCountry()
        rc.code = code["code"]
        rc.text = code["name"]
        db.session.add(rc)
    db.session.commit()

def import_budget_types(lang): 
    filename="budget_type_EN_FR.csv"
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib/'+filename), 'r') as csvfile:
        budgettypereader = unicodecsv.DictReader(csvfile)
        for row in budgettypereader:
            nc = models.BudgetType()
            nc.code = row["Code"]
            nc.text = row[lang + "_Name"]
            db.session.add(nc)
    db.session.commit()
