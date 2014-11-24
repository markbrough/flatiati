#!/usr/bin/env python

from lxml import etree
import urllib2
import os
from abmapper import app, db
from abmapper import models
from abmapper.lib import codelists
import unicodecsv
from sqlalchemy import func, distinct
import xlrd

def projects(country_code, reporting_org=None):
    if not reporting_org:
        p = models.Activity.query.filter_by(
                recipient_country_code=country_code
            ).all()
    else:
        p = models.Activity.query.filter_by(
                recipient_country_code=country_code,
                reporting_org_ref=reporting_org
            ).all()
        
    return p

def update_project(data):
    f = data.filename
    print "Trying to read %s" % f
    sheetname = "Raw data export"
    book = xlrd.open_workbook(filename=f)
    sheet = book.sheet_by_name(sheetname)
    project_data = {}
    for i in range(1, sheet.nrows):
        if sheet.cell_type(i, 0)==1:
            # Start collecting project data
            project_id = sheet.cell(i, 0).value

            project_data[project_id] = {"num_sectors": 0}
            for checkrow in range(i+1, sheet.nrows):
                if sheet.cell_type(checkrow, 0)==0:
                    project_data[project_id]["num_sectors"]+=1

                if sheet.cell_type(checkrow, 0)==1:
                    break
            
            project_data[project_id]["sectors"] = []

            for si in range(i, i+project_data[project_id]["num_sectors"]):
                project_data[project_id]["sectors"].append(
                    {
                    "cc_id": sheet.cell(i, 5).value
                    }
                )

            # End collecting project data
        if sheet.cell_type(i, 0)==0: continue
    print project_data

    # Check existing list of projects and get sectors from there
    

def country(country_code):
    c = models.RecipientCountry.query.filter_by(code=country_code).first()
    return c

def countries_activities():
    c = db.session.query(func.count(models.Activity.id).label("num_activities"),
                         models.RecipientCountry
                    ).join(models.RecipientCountry
                    ).group_by(models.RecipientCountry
                    ).all()
    return c

def reporting_org_activities(country_code):
    r = db.session.query(distinct(models.Activity.reporting_org_ref).label("reporting_org"),
                         func.count(models.Activity.id).label("num_activities"),
                    ).filter(models.Activity.recipient_country_code==country_code
                    ).group_by(models.Activity.reporting_org_ref
                    ).all()
    return r

def project(iati_identifier):
    p = p = models.Activity.query.filter_by(
        iati_identifier=iati_identifier
        ).first_or_404()
    return p

def mappable():
    csql = """select count(activity.id) from activity;"""
    
    msql = """select count(activity.id) from activity 
            left join sector on
              activity.iati_identifier=sector.activity_iati_identifier 
            left join dacsector on 
              sector.code=dacsector.code
            left join commoncode on 
              dacsector.cc_id=commoncode.id 
            where cc_id >0;"""

    counta = db.engine.execute(csql).first()[0]
    countm = db.engine.execute(msql).first()[0]

    total = float(countm)/float(counta)*100
    return {"all": counta, 
            "mapped": countm, 
            "total": total}

def DAC_codes():
    s = db.session.query(models.DACSector.code).all()
    return zip(*s)[0]

def DAC_codes_existing():
    codes = []
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib/oecd_dac_sectors.csv'), 'r') as csvfile:
        crsreader = unicodecsv.DictReader(csvfile)
        for row in crsreader:
            if row["CRS CODE"] != "":
                codes.append(int(row["CRS CODE"]))
    return codes

def DAC_codes_old_new():
    mapped_DAC_codes = DAC_codes()

    existing_DAC_codes = DAC_codes_existing()

    count = 0
    for code in existing_DAC_codes:
        if code not in mapped_DAC_codes:
            print "%s not found" % (code)
            count +=1
    print "%s codes not found" % (count)

def DAC_codes_cc_mappable():
    s = db.session.query(models.DACSector.code,
                         models.DACSector.description,
                         models.CommonCode.id
            ).outerjoin(models.CommonCode
            ).order_by(models.DACSector.code
            ).all()
    return s

def sector(sector_code):
    sector_code=int(sector_code)
    s = db.session.query(models.DACSector.code,
                         models.DACSector.description,
                         models.CommonCode.id,
                         models.CommonCode.function,
                         models.CommonCode.sector,
            ).outerjoin(models.CommonCode
            ).filter(models.DACSector.code==sector_code
            ).first()
    return s

def add_sector_to_project(sector_code, iati_identifier, percentage):
    checkS = db.session.query(models.Sector
            ).filter(models.Sector.activity_iati_identifier==iati_identifier
            ).filter(models.Sector.code==sector_code
            ).first()
    if checkS:
        return False
    newS = models.Sector()
    newS.code = sector_code
    newS.percentage = percentage
    newS.activity_iati_identifier = iati_identifier
    newS.edited = True
    db.session.add(newS)
    db.session.commit()
    return newS

def delete_sector_from_project(sector_code, iati_identifier):
    checkS = db.session.query(models.Sector
            ).filter(models.Sector.activity_iati_identifier==iati_identifier
            ).filter(models.Sector.code==sector_code
            ).first() 
    if not checkS:
        return False

    # Delete manually added sectors, but just mark sectors in the original
    # IATI data as deleted, don't delete them.

    print "checks was edited", checkS.edited
    if checkS.edited == True:
        db.session.delete(checkS)
        db.session.commit()
        return "deleted"

    checkS.deleted = True
    db.session.add(checkS)
    db.session.commit()
    return "marked as deleted"

def restore_sector_to_project(sector_code, iati_identifier):
    checkS = db.session.query(models.Sector
            ).filter(models.Sector.activity_iati_identifier==iati_identifier
            ).filter(models.Sector.code==sector_code
            ).first() 
    if not checkS:
        return False

    checkS.deleted = False
    db.session.add(checkS)
    db.session.commit()
    return True
