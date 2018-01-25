# -*- coding: utf-8 -*-
from abmapper import db
from abmapper.query import models
import unicodecsv
import os
import urllib2
import json
from flask import abort
import exchangerates
from datetime import datetime

CODELIST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../lib/codelists/{}.csv')

def trash():
    db.drop_all()

def update_codelists():
    codelists = {
        "ActivityStatus": "http://iatistandard.org/202/codelists/downloads/clv2/csv/en/ActivityStatus.csv",
        "AidType": "https://andylolz.github.io/dac-crs-codes/data/aid_type.csv",
        "Country": "https://github.com/datasets/country-codes/raw/master/data/country-codes.csv",
        "Sector_en": "http://iatistandard.org/202/codelists/downloads/clv3/csv/en/Sector.csv",
        "Sector_fr": "http://iatistandard.org/202/codelists/downloads/clv3/csv/fr/Sector.csv",
        "SectorCategory_en": "http://iatistandard.org/202/codelists/downloads/clv3/csv/en/SectorCategory.csv",
        "SectorCategory_fr": "http://iatistandard.org/202/codelists/downloads/clv3/csv/fr/SectorCategory.csv",
        "CollaborationType": "https://andylolz.github.io/dac-crs-codes/data/collaboration_type.csv",
        "FinanceType": "https://andylolz.github.io/dac-crs-codes/data/finance_type.csv",
        "FinanceType_old": "https://raw.githubusercontent.com/markbrough/IATI-Codelists-NonEmbedded/CRS-codelists-en-fr/csv/FinanceType.csv",
        "FiscalYears": "https://raw.githubusercontent.com/markbrough/country-fiscal-years/gh-pages/data/countries_fiscal_years.csv",
        "DocumentCategory_en": "http://iatistandard.org/202/codelists/downloads/clv3/csv/en/DocumentCategory.csv",
        "DocumentCategory_fr": "http://iatistandard.org/202/codelists/downloads/clv3/csv/fr/DocumentCategory.csv",
    }
    for code, url in codelists.items():
        print("Fetching codelist {} from {}".format(code, url))
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
    import_collaboration_types()
    import_finance_types()
    import_reporting_organisations()
    create_fallback_codes()
    #import_document_categories()

def import_sectors():
    SectorCategories = {}
    with open(CODELIST_PATH.format("SectorCategory_en"), 'r') as scfile:
        for row in unicodecsv.DictReader(scfile):
            row["name_en"] = row["name"]
            row["description_en"] = row["description"]
            SectorCategories[row["code"]] = row

    with open(CODELIST_PATH.format("SectorCategory_fr"), 'r') as scfile:
        for row in unicodecsv.DictReader(scfile):
            SectorCategories[row["code"]]["name_fr"] = row["name"]
            SectorCategories[row["code"]]["description_fr"] = row["description"]

    with open(CODELIST_PATH.format("Sector_en"), 'r') as sfile:
        for row in unicodecsv.DictReader(sfile):
            dacsector = models.DACSector()
            dacsector.code = row["code"]
            dacsector.dac_five_code = SectorCategories[row["category"]]["code"]
            dacsector.dac_five_name_EN = SectorCategories[row["category"]]["name_en"]
            dacsector.dac_five_name_FR = SectorCategories[row["category"]]["name_fr"]
            dacsector.description_EN = row["name"]
            dacsector.notes_EN = row["description"]
            db.session.add(dacsector)
        db.session.commit()

    with open(CODELIST_PATH.format("Sector_fr"), 'r') as sfile:
        for row in unicodecsv.DictReader(sfile):
            dacsector = models.DACSector.query.filter_by(code=row["code"]
                        ).first()
            dacsector.code = row["code"]
            dacsector.description_FR = row["name"]
            dacsector.notes_FR = row["description"]
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

def import_collaboration_types():
    with open(CODELIST_PATH.format("CollaborationType"), 'r') as csvfile:
        collabtypereader = unicodecsv.DictReader(csvfile)
        for row in collabtypereader:
            nc = models.CollaborationType()
            nc.code = row["code"]
            nc.text_EN = row["name_en"]
            nc.text_FR = row["name_fr"]
            db.session.add(nc)
    db.session.commit()

def import_finance_types():
    with open(CODELIST_PATH.format("FinanceType"), 'r') as csvfile:
        financetypereader = unicodecsv.DictReader(csvfile)
        for row in financetypereader:
            nc = models.FinanceType()
            nc.code = row["code"]
            nc.text_EN = row["name_en"]
            nc.text_FR = row["name_fr"]
            db.session.add(nc)
    with open(CODELIST_PATH.format("FinanceType_old"), 'r') as csvfile:
        financetypereader = unicodecsv.DictReader(csvfile)
        for row in financetypereader:
            if not models.FinanceType.query.filter_by(code=row["code"]).first():
                nc = models.FinanceType()
                nc.code = row["code"]
                nc.text_EN = row["name_en"]
                nc.text_FR = row["name_fr"]
                db.session.add(nc)
    db.session.commit()

def import_recipient_countries():
    with open(CODELIST_PATH.format("Country"), 'r') as csvfile:
        countryreader = unicodecsv.DictReader(csvfile)
        for row in countryreader:
            if (row["official_name_en"] == "") or (row["ISO3166-1-Alpha-2"] == ""): continue
            rc = models.RecipientCountry()
            rc.code = row["ISO3166-1-Alpha-2"]
            rc.text_EN = row["official_name_en"]
            rc.text_FR = row["official_name_fr"]
            db.session.add(rc)
    ADDITIONAL_COUNTRIES = [{
        "code": u"KV",
        "text_EN": u"Kosovo",
        "text_FR": u"Kosovo"
    },{
        "code": u"XK",
        "text_EN": u"Kosovo",
        "text_FR": u"Kosovo"
    }]
    for country in ADDITIONAL_COUNTRIES:
        rc = models.RecipientCountry()
        rc.code = country["code"]
        rc.text_EN = country["text_EN"]
        rc.text_FR = country["text_FR"]
        db.session.add(rc)
    with open(CODELIST_PATH.format("FiscalYears"), 'r') as csvfile:
        countryreader = unicodecsv.DictReader(csvfile)
        for row in countryreader:
            country = models.RecipientCountry.query.filter_by(code=row["code"]
                        ).first()
            if not country: continue
            if row["fy_start"] == "Unknown": continue
            month_offset = datetime.strptime(row["fy_start"], "%d %B").month-1
            country.fiscalyear_modifier = month_offset
            db.session.add(country)
    db.session.commit()

def import_budget_mappings():
    bms = [{
        "order": 1,
        "name": u"Agency",
        "recipientcountry_code": u"LR",
        "is_constant": False,
        "maps_to": 1
    },
    {
        "order": 2,
        "name": u"Budget Classification",
        "recipientcountry_code": u"LR",
        "is_constant": True,
        "constant_value": u"6"
    },
    {
        "order": 3,
        "name": u"Fund Type",
        "recipientcountry_code": u"LR",
        "is_constant": True,
        "constant_value": u"01"
    },
    {
        "order": 5,
        "name": u"Project",
        "recipientcountry_code": u"LR",
        "is_constant": True,
        "constant_value": u"000000"
    },
    ]
    for bm in bms:
        m = models.BudgetMapping()
        m.order = bm["order"]
        m.name = bm["name"]
        m.recipientcountry_code = bm["recipientcountry_code"]
        m.is_constant = bm["is_constant"]
        if bm.get("is_constant"):
            m.constant_value = bm["constant_value"]
        else:
            m.maps_to = bm["maps_to"]
        db.session.add(m)
    db.session.commit()
    
    the_bm = models.BudgetMapping.query.filter_by(name=u"Agency").first()
    with open(CODELIST_PATH.format("liberia/sector_agency"), 'r') as csvfile:
        mappingreader = unicodecsv.DictReader(csvfile)
        for row in mappingreader:
            nmc = models.BudgetMappingDACCode()
            nmc.budgetmapping_id = the_bm.id
            nmc.dacsector_code = row["code"]
            nmc.code = row["agency_code"]
            nmc.name = row["agency_name"]
            db.session.add(nmc)
    db.session.commit()

def import_reporting_organisations():
    with open(CODELIST_PATH.format("ReportingOrganisation"), 'r') as csvfile:
        roreader = unicodecsv.DictReader(csvfile)
        for row in roreader:
            nc = models.ReportingOrg()
            nc.code = row["code"]
            nc.text_EN = row["text_en"]
            nc.text_FR = row["text_fr"]
            nc.active = bool(row["active"])
            db.session.add(nc)
    db.session.commit()

def import_document_categories():
    with open(CODELIST_PATH.format("DocumentCategory_en"), 'r') as csvfile:
        roreader = unicodecsv.DictReader(csvfile)
        for row in roreader:
            nc = models.DocumentCategory()
            nc.code = row["code"]
            nc.text_EN = row["name"]
            nc.activity_doc = bool(row["category"] == "A")
            db.session.add(nc)
    with open(CODELIST_PATH.format("DocumentCategory_fr"), 'r') as csvfile:
        roreader = unicodecsv.DictReader(csvfile)
        for row in roreader:
            nc = models.DocumentCategory.query.filter_by(code=row["code"]
                        ).first()
            nc.text_FR = row["name"]
            db.session.add(nc)
    db.session.commit()

def create_fallback_codes():
    for nc in [models.FinanceType(), models.CollaborationType()]:
        nc.code = 0
        nc.text_EN = u"Unknown"
        nc.text_FR = u"Inconnu"
        db.session.add(nc)
    for nc in [models.AidType(), models.RecipientCountry()]:
        nc.code = "0"
        nc.text_EN = u"Unknown"
        nc.text_FR = u"Inconnu"
        db.session.add(nc)
    dacsector = models.DACSector()
    dacsector.code = 0
    dacsector.dac_five_code = 0
    dacsector.dac_five_name_EN = u"Unknown"
    dacsector.dac_five_name_FR = u"Inconnu"
    dacsector.description_EN = u"Unknown"
    dacsector.notes_EN = u"Unknown"
    dacsector.description_FR = u"Inconnu"
    dacsector.notes_FR = u"Inconnu"
    db.session.add(dacsector)
    db.session.commit()

def update_exchange_rates():
    exchangerates.CurrencyConverter(update=True)
