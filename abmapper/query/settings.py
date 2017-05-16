# -*- coding: utf-8 -*-
from abmapper import db
from abmapper.query import models
import unicodecsv
import os
import urllib2
import json
from flask import abort

def reporting_orgs():
    return models.ReportingOrg.query.all()

def reporting_org_by_id(reporting_org_id):
    return models.ReportingOrg.query.filter_by(
        id=reporting_org_id
    ).first()

def reporting_org_by_code(reporting_org_code):
    return models.ReportingOrg.query.filter_by(
        code=reporting_org_code
    ).first()

def add_reporting_org(reporting_org_code):
    ro = models.ReportingOrg()
    ro.code = reporting_org_code
    ro.text_EN = reporting_org_code
    ro.text_FR = reporting_org_code
    db.session.add(ro)
    db.session.commit()
    return ro.id

def delete_reporting_org(reporting_org_id):
    ro = models.ReportingOrg.query.filter_by(
        id=reporting_org_id
    ).first()
    if ro.num_activities > 0:
        activities = models.Activity.query.filter_by(
            reporting_org_id = reporting_org_id
        ).all()
        for activity in activities:
            db.session.delete(activity)
        db.session.commit()
    if ro:
        db.session.delete(ro)
        db.session.commit()
        return True
    return False

def update_reporting_org_attr(data):
    reporting_org = models.ReportingOrg.query.filter_by(
        id = data['reporting_org_id']
    ).first()
    setattr(reporting_org, data['attr'], data['value'])
    db.session.add(reporting_org)
    db.session.commit()
    return True