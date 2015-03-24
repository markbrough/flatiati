#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abmapper import app, db
from abmapper.query import models
import unicodecsv

def DAC_codes():
    s = db.session.query(models.DACSector.code).all()
    return zip(*s)[0]

def DAC_codes_existing():
    codes = []
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 'lib/oecd_dac_sectors.csv'), 'r') as csvfile:
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

def add_sector_to_project(sector_code, iati_identifier, percentage, 
                          formersector_id=None, assumed=False):
    checkS = db.session.query(models.Sector
            ).filter(
            models.Sector.activity_iati_identifier==iati_identifier
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
    newS.formersector_id = formersector_id
    db.session.add(newS)
    db.session.commit()
    return newS

def delete_sector_from_project(sector_code, iati_identifier):
    checkS = db.session.query(models.Sector
            ).filter(
            models.Sector.activity_iati_identifier==iati_identifier
            ).filter(models.Sector.code==sector_code
            ).first() 
    if not checkS:
        return False

    # Delete manually added sectors, but just mark sectors in the original
    # IATI data as deleted, don't delete them.

    if checkS.edited == True:
        db.session.delete(checkS)
        db.session.commit()
        return True

    checkS.deleted = True
    db.session.add(checkS)
    db.session.commit()
    return checkS.id

def restore_sector_to_project(sector_code, iati_identifier):
    checkS = db.session.query(models.Sector
            ).filter(
            models.Sector.activity_iati_identifier==iati_identifier
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