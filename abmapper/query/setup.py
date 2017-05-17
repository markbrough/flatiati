# -*- coding: utf-8 -*-
from abmapper import db
from abmapper.query import models
import unicodecsv
import os
import urllib2
import json
from flask import abort

CODELIST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../lib/codelists/{}.csv')

def trash():
    db.drop_all()

def update_codelists():
    codelists = {
        "ActivityStatus": "http://iatistandard.org/202/codelists/downloads/clv2/csv/en/ActivityStatus.csv",
        "AidType": "https://andylolz.github.io/dac-crs-codes/data/aid_type.csv",
        "Country": "https://github.com/datasets/country-codes/raw/master/data/country-codes.csv",
        "Sector": "https://andylolz.github.io/dac-crs-codes/data/sector.csv",
        "SectorCategory": "https://andylolz.github.io/dac-crs-codes/data/sector_category.csv"
    }
    for code, url in codelists.items():
        sourcedata = urllib2.urlopen(url, timeout=60).read()
        path = CODELIST_PATH.format(code)
        with file(path, 'w') as localFile:
            localFile.write(sourcedata)

def setup():
    db.create_all()
    import_sectors()
    import_activity_statuses()
    import_aid_types()
    import_recipient_countries()
    import_budget_types()

def import_sectors():
    SectorCategories = {}
    with open(CODELIST_PATH.format("SectorCategory"), 'r') as scfile:
        for row in unicodecsv.DictReader(scfile):
            SectorCategories[row["code"]] = row

    with open(CODELIST_PATH.format("Sector"), 'r') as sfile:
        for row in unicodecsv.DictReader(sfile):
            dacsector = models.DACSector()
            if row["voluntary_code"] != "": 
                dacsector.code = row["voluntary_code"]
            else:
                dacsector.code = row["code"]
            #dacsector.dac_sector_code = row["DAC_sector_code"] #NO
            #dacsector.dac_sector_name_EN = row["DAC_sector_name"] #NO
            #dacsector.dac_sector_name_FR = row["DAC_sector_name"] #NO
            dacsector.dac_five_code = SectorCategories[row["category"]]["code"]
            dacsector.dac_five_name_EN = SectorCategories[row["category"]]["name_en"]
            dacsector.dac_five_name_FR = SectorCategories[row["category"]]["name_fr"]
            dacsector.description_EN = row["name_en"]
            dacsector.description_FR = row["name_fr"]
            dacsector.notes_EN = row["description_en"]
            dacsector.notes_FR = row["description_fr"]
            db.session.add(dacsector)
        db.session.commit()

def import_activity_statuses():
    with open(CODELIST_PATH.format("ActivityStatus"), 'r') as csvfile:
        statusreader = unicodecsv.DictReader(csvfile)
        for row in statusreader:
            activitystatus = models.ActivityStatus()
            activitystatus.code = row["code"]
            activitystatus.text_EN = row["name"]
            activitystatus.text_FR = row["name"]
            db.session.add(activitystatus)
        db.session.commit()

def import_aid_types():
    with open(CODELIST_PATH.format("AidType"), 'r') as csvfile:
        aidtypereader = unicodecsv.DictReader(csvfile)
        for row in aidtypereader:
            nc = models.AidType()
            nc.code = row["code"]
            nc.text_EN = row["name_en"]
            nc.text_FR = row["name_fr"]
            db.session.add(nc)
    db.session.commit()

def import_recipient_countries():
    with open(CODELIST_PATH.format("Country"), 'r') as csvfile:
        countryreader = unicodecsv.DictReader(csvfile)
        for row in countryreader:
            if (row["name"] == "") or (row["ISO3166-1-Alpha-2"] == ""): continue
            rc = models.RecipientCountry()
            rc.code = row["ISO3166-1-Alpha-2"]
            rc.text_EN = row["official_name_en"]
            rc.text_FR = row["official_name_fr"]
            db.session.add(rc)
    db.session.commit()

def import_budget_types():
    filename="budget_type_EN_FR.csv"
    with open(CODELIST_PATH.format("budget_type_EN_FR"), 'r') as csvfile:
        budgettypereader = unicodecsv.DictReader(csvfile)
        for row in budgettypereader:
            nc = models.BudgetType()
            nc.code = row["Code"]
            nc.text_EN = row["EN_Name"]
            nc.text_FR = row["FR_Name"]
            db.session.add(nc)
    db.session.commit()