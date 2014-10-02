#!/usr/bin/env python

from lxml import etree
import urllib2
import os
from abmapper import app, db
from abmapper import models

def projects():
    p = models.Activity.query.all()
    return p

def project(iati_identifier):
    p = p = models.Activity.query.filter_by(
        iati_identifier=iati_identifier
        ).first()
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
