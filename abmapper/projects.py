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

def a_not_in_b(a, b):
    def filterer(a):
        return a not in b
    return filter(filterer, a)

def deleted_sector_codes_from_cc(deleted_ccs, project_sectors):
    def filterer(project_sector):
        return (project_sector.dacsector.cc_id in deleted_ccs
                                    ) and (project_sector.deleted==False)
    return filter(filterer, project_sectors)

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def number_or_none(s):
    if s=="":
        return 0.00
    if is_number(s):
        return float(s)
    return None

def get_first(list):
    if list is None:
        return None
    return list[0]

def correct_zeros(value):
    if str(value) == "0.0":
        return "0"
    return value

def none_is_zero(value):
    try:
        return float(value)
    except TypeError:
        return 0.0

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
            capital_spend = number_or_none(sheet.cell(i, 13).value)

            # There must always be at least 1 sector-row (because of the title,
            # etc.)

            project_data[project_id] = {"num_sectors": 1}
            project_data[project_id]["capital_spend"] = capital_spend

            for checkrow in range(i+1, sheet.nrows):
                if sheet.cell_type(checkrow, 0)==0:
                    project_data[project_id]["num_sectors"]+=1

                if sheet.cell_type(checkrow, 0)==1:
                    break
            
            project_data[project_id]["sectors"] = []

            for si in range(i, i+project_data[project_id]["num_sectors"]):
                project_data[project_id]["sectors"].append(
                    {
                    "cc_id": correct_zeros(sheet.cell(si, 5).value),
                    "percentage": "UNKNOWN",
                    }
                )

            # End collecting project data
        if sheet.cell_type(i, 0)==0: 
            continue

    for project_identifier, sectors in project_data.items():
        try:
            p = project(project_identifier)
        except Exception, e:
            print "UNKNOWN PROJECT", project_identifier
            continue

        new_sectors = dict(map(lambda s: (s["cc_id"], s["percentage"]), sectors['sectors']))
        existing_sectors = dict(map(lambda s: (s.dacsector.cc_id, s.percentage), p.sectors))
        
        added_sectors = a_not_in_b(new_sectors, existing_sectors)
        deleted_sectors = a_not_in_b(existing_sectors, new_sectors)


        # Update capital expenditure
        p = project(project_identifier)
        p.capital_exp = sectors["capital_spend"]
        db.session.add(p)
        db.session.commit()

        if deleted_sectors or added_sectors:
            # Need to update this project
            """print project_identifier
            print "sectors are", sectors
            print "Added sectors", added_sectors
            print "Deleted sectors", deleted_sectors"""


        if deleted_sectors:
            # 1 Find sectors related to deleted CCs for this project

            # Filter out sectors not related deleted CCs, or already deleted
            crs_codes_for_deletion = map(lambda s: s.dacsector.code, 
                    deleted_sector_codes_from_cc(deleted_sectors, p.sectors))

            # 2 Mark those sectors as deleted

            [delete_sector_from_project(sector_code, project_identifier) for 
                                        sector_code in crs_codes_for_deletion]

        if added_sectors:   
            # 3 Get pct of remaining percentage
            unused_sector_pct = get_unused_sector_percentage(project_identifier)

            # 4 Set default percentage value for new added sectors (divide total
            # available amount by number of added sectors)

            default_sector_pct = float(unused_sector_pct)/len(added_sectors)
            if default_sector_pct<=0: print "ALERT: 0 VALUE SECTORS"


            for addsector in added_sectors:
                # 5 Get a random sector associated with this CC
                newsector_code = get_sector_from_cc(addsector)
                if not newsector_code:
                    print "UNRECOGNISED CC ID", addsector
                    continue
                print "New sector is", addsector

                # 6 Add that sector to the project, but mark it as assumed

                def getRelevantSector(sector):
                    return sector["cc_id"] == addsector

                relevant_sector = get_first(filter(getRelevantSector, sectors['sectors']))
                if is_number(relevant_sector["percentage"]):
                    percentage = relevant_sector["percentage"]
                else:
                    percentage = default_sector_pct

                add_sector_to_project(newsector_code, project_identifier, percentage, True)
        
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

def add_sector_to_project(sector_code, iati_identifier, percentage, assumed=False):
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
    newS.assumed = assumed
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

def get_unused_sector_percentage(iati_identifier):
    checkS = db.session.query(models.Sector.percentage
        ).filter(models.Sector.activity_iati_identifier==iati_identifier
        ).filter(models.Sector.deleted==False
        ).all() 
    checkSvalues = map(lambda s: s.percentage, checkS)
    total_pct = sum(checkSvalues)
    return 100-total_pct

def get_sector_from_cc(cc_id):
    checkS = db.session.query(models.DACSector.code
            ).join(models.CommonCode
            ).filter(models.CommonCode.id==cc_id
            ).first()
    if not checkS:
        return False
    return checkS.code

def country_project_stats(country_code, aid_types=["C01", "D01", "D02"], 
                                        activity_statuses=[2]):

    p = projects(country_code)

    def aid_type_filter(the_project):
        return (the_project.aid_type_code in aid_types) and (
                    the_project.status_code in activity_statuses)

    p = filter(aid_type_filter, p)

    total_value = sum(map(lambda project: none_is_zero(project.total_commitments), p))
    total_mappable_before = sum(map(lambda project: none_is_zero(project.pct_mappable_before)/100 * 
                none_is_zero(project.total_commitments), p))
    total_mappable_after = sum(map(lambda project: none_is_zero(project.pct_mappable_after)/100 * 
                none_is_zero(project.total_commitments), p))
    return {"total_value": "{:,}".format(total_value),
            "total_mappable_before": total_mappable_before,
            "total_mappable_before_pct": round(total_mappable_before/total_value*100, 2),
            "total_mappable_after": total_mappable_after,
            "total_mappable_after_pct": round(total_mappable_after/total_value*100, 2),
           }
