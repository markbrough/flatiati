#!/usr/bin/env python
# -*- coding: utf-8 -*-

from lxml import etree
import urllib2
import os
from abmapper import app, db
from abmapper.query import models
from abmapper.query import sectors
from abmapper.lib import codelists
import unicodecsv
from sqlalchemy import func, distinct

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
    
def country(country_code):
    c = models.RecipientCountry.query.filter_by(code=country_code).first()
    return c

def countries_activities():
    c = db.session.query(
                func.count(models.Activity.id).label("num_activities"),
                models.RecipientCountry
            ).join(models.RecipientCountry
            ).group_by(models.RecipientCountry
            ).all()
    return c

def reporting_org_activities(country_code):
    r = db.session.query(
        distinct(models.Activity.reporting_org_ref).label("reporting_org"),
        func.count(models.Activity.id).label("num_activities"),
        ).filter(models.Activity.recipient_country_code==country_code
                    ).group_by(models.Activity.reporting_org_ref
                    ).all()
    return r

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
