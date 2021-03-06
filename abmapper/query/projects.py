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
        p = models.Activity.query.filter(
                models.RecipientCountries.recipient_country_code==country_code
            ).join(models.RecipientCountries
            ).all()
    else:
        p = models.Activity.query.filter(
                models.RecipientCountries.recipient_country_code==country_code,
                models.Activity.reporting_org_id==reporting_org
            ).join(models.RecipientCountries
            ).all()
    return p

def country(country_code):
    c = models.RecipientCountry.query.filter_by(code=country_code).first()
    return c

def countries_active():
    c = models.RecipientCountry.query.filter_by(active=True).all()
    return list(map(lambda c: c.code, c))

def countries_activities():
    c = db.session.query(
                models.RecipientCountry,
                models.RecipientCountries,
                func.count(models.Activity.iati_identifier).label("num_activities")
            ).outerjoin(models.RecipientCountries
            ).outerjoin(models.Activity
            ).filter(models.RecipientCountry.active==True
            ).group_by(models.RecipientCountry
            ).order_by("num_activities DESC"
            ).order_by(models.RecipientCountry.code
            ).all()
    return c

def reporting_org_activities(country_code):
    reporting_orgs = models.ReportingOrg.query.order_by(
                models.ReportingOrg.text
            ).all()
    r = list(map(lambda x: {
                "id": x.id,
                "code": x.code,
                "text": x.text,
                "num_activities": x.num_activities}, reporting_orgs))
    return r

def project(iati_identifier):
    p = models.Activity.query.filter_by(
        iati_identifier=iati_identifier
        ).first()
    return p
