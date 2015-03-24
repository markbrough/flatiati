# -*- coding: utf-8 -*-
from abmapper import db
from abmapper.query import models
import unicodecsv
import os
import urllib2
import json
from flask import abort

CODELISTS_API = "http://iatistandard.org/codelists/downloads/clv2/json/%s/%s.json"

def setup():
    db.create_all()
    import_common_code()
    import_sectors()
    import_activity_statuses()
    import_aid_types()
    import_recipient_countries()
    import_budget_types()

def import_common_code():
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../lib/CC_EN_FR.csv'), 'r') as csvfile:
        ccreader = unicodecsv.DictReader(csvfile)
        for row in ccreader:
            cc = models.CommonCode()
            cc.id = row["CC code"]
            cc.category_EN = row["Category of Government"]
            cc.sector_EN = row["Sector"]
            cc.function_EN = row["Function"]    
            cc.category_FR = row["Categorie de gouvernement"]
            cc.sector_FR = row["Secteur"]
            cc.function_FR = row["Fonction"]
            db.session.add(cc)
        db.session.commit()

def import_sectors():
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     '../lib/crs_cc_EN.csv'), 'r') as csvfile:
        crsccreader = unicodecsv.DictReader(csvfile)
        for row in crsccreader:
            crscc = models.DACSector()
            crscc.code = row["CRS_code"]
            crscc.dac_sector_code = row["DAC_sector_code"]
            crscc.dac_sector_name_EN = row["DAC_sector_name"]
            crscc.dac_five_code = row["DAC_5_code"]
            crscc.dac_five_name_EN = row["DAC_5_name"]
            crscc.description_EN = row["DESCRIPTION"]
            crscc.notes_EN = row["notes"]
            crscc.parent_code = row["parent_code"]
            crscc.cc_id = row["cc_id"]
            db.session.add(crscc)
        db.session.commit()
    # Get FR sector names
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../lib/crs_cc_FR.csv'), 'r') as csvfile:
        crsccreader = unicodecsv.DictReader(csvfile)
        for row in crsccreader:
            crscc = models.DACSector.query.filter_by(
                code=row["CRS_code"]).first()
            crscc.dac_sector_name_FR = row["DAC_sector_name"]
            crscc.dac_five_name_FR = row["DAC_5_name"]
            crscc.description_FR = row["DESCRIPTION"]
            crscc.notes_FR = row["notes"]
            db.session.add(crscc)
        db.session.commit()

def import_activity_statuses():
    aid_type_url = CODELISTS_API % ("en", 'ActivityStatus')
    sourcedata = urllib2.urlopen(aid_type_url, timeout=60).read()
    data = json.loads(sourcedata)['data']
    for code in data:
        activitystatus = models.ActivityStatus()
        activitystatus.code = code["code"]
        activitystatus.text_EN = code["name"]
        db.session.add(activitystatus)
    db.session.commit()
    aid_type_url = CODELISTS_API % ("fr", 'ActivityStatus')
    sourcedata = urllib2.urlopen(aid_type_url, timeout=60).read()
    data = json.loads(sourcedata)['data']
    for code in data:
        activitystatus = models.ActivityStatus.query.filter_by(
            code = code["code"]
        ).first()
        activitystatus.text_FR = code["name"]
        db.session.add(activitystatus)
    db.session.commit()

def import_aid_types(): 
    filename="aid_type_EN_FR.csv"
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../lib/'+filename), 'r') as csvfile:
        aidtypereader = unicodecsv.DictReader(csvfile)
        for row in aidtypereader:
            nc = models.AidType()
            nc.code = row["Code"]
            nc.text_EN = row["EN_Description"]
            nc.text_FR = row["FR_Description"]
            db.session.add(nc)
    db.session.commit()

def import_recipient_countries():
    # Only EN available via IATI API
    aid_type_url = CODELISTS_API % ("en", 'Country')
    sourcedata = urllib2.urlopen(aid_type_url, timeout=60).read()
    data = json.loads(sourcedata)['data']
    for code in data:
        rc = models.RecipientCountry()
        rc.code = code["code"]
        rc.text_EN = code["name"]
        rc.text_FR = code["name"]
        db.session.add(rc)
    db.session.commit()

def import_budget_types():
    filename="budget_type_EN_FR.csv"
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../lib/'+filename), 'r') as csvfile:
        budgettypereader = unicodecsv.DictReader(csvfile)
        for row in budgettypereader:
            nc = models.BudgetType()
            nc.code = row["Code"]
            nc.text_EN = row["EN_Name"]
            nc.text_FR = row["FR_Name"]
            db.session.add(nc)
    db.session.commit()