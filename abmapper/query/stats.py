#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abmapper import app, db
from abmapper.lib import country_colours
from abmapper.lib import util
import projects as abprojects

def budget_project_stats(country_code, budget_type):
    # GET SQL
    # CALCULATE BEFORE, AFTER
    sql = """
    SELECT sum(atransaction.value*sector.percentage/100) AS sum_value,
    budgetcode.code, budgetcode.name
    FROM atransaction
    JOIN activity ON 
        activity.id=atransaction.activity_iati_identifier
    JOIN sector ON 
        activity.id = sector.activity_iati_identifier
    JOIN dacsector ON sector.code = dacsector.code
    JOIN commoncode ON dacsector.cc_id = commoncode.id
    JOIN ccbudgetcode ON commoncode.id = ccbudgetcode.cc_id
    JOIN budgetcode ON ccbudgetcode.budgetcode_id = budgetcode.id
    WHERE sector.deleted = 0
    AND activity.recipient_country_code="%s"
    AND activity.aid_type_code IN ('C01', 'D01', 'D02')
    AND activity.status_code IN (2, 3)
    AND atransaction.transaction_type_code="C"
    AND budgetcode.country_code = "%s"
    AND budgetcode.budgettype_code = "%s"
    GROUP BY budgetcode.code
    ;"""

    sql_before = """
    SELECT sum(atransaction.value*sector.percentage/100) AS sum_value,
    budgetcode.code, budgetcode.name
    FROM atransaction
    JOIN activity ON activity.id=atransaction.activity_iati_identifier
    JOIN sector ON activity.id = sector.activity_iati_identifier
    JOIN dacsector ON sector.code = dacsector.code
    JOIN commoncode ON dacsector.cc_id = commoncode.id
    JOIN ccbudgetcode ON commoncode.id = ccbudgetcode.cc_id
    JOIN budgetcode ON ccbudgetcode.budgetcode_id = budgetcode.id
    WHERE sector.edited = 0
    AND activity.recipient_country_code="%s"
    AND activity.aid_type_code IN ('C01', 'D01', 'D02')
    AND activity.status_code IN (2, 3)
    AND atransaction.transaction_type_code="C"
    AND budgetcode.country_code = "%s"
    AND budgetcode.budgettype_code = "%s"
    GROUP BY budgetcode.code
    ;"""

    sql_total = """
    SELECT sum(atransaction.value) AS sum_value
    FROM atransaction
    JOIN activity ON 
        activity.id=atransaction.activity_iati_identifier
    AND activity.recipient_country_code="%s"
    AND activity.aid_type_code IN ('C01', 'D01', 'D02')
    AND activity.status_code IN (2, 3)
    AND atransaction.transaction_type_code="C"
    ;"""

    after = db.engine.execute(sql % (
                country_code, country_code, budget_type)
                )
    before = db.engine.execute(sql_before % (
                country_code, country_code, budget_type)
                )
    total = db.engine.execute(sql_total % (
                country_code
                )).first()[0]

    if not total:
        return {
            "total": 0,
            "budgets": {
                "-": {
                    'code': '-',
                    'name': "Unknown",
                    'before': {
                        'value': 0.00,
                        'pct': 0.00
                    },
                    'after': {
                        'value': 0.00,
                        'pct': 0.00
                    }
                }
            }
        }

    stats = {'total': total,
             'budgets': {}}
        
    unknown_value_before = total or 0
    unknown_value_after = total or 0

    for b in before:
        if b.code not in stats['budgets']:
            stats['budgets'][b.code] = {
                'code': util.nulltoDash(b.code),
                'name': util.nulltoUnknown(b.name),
                'after': {'value': 0.00, 'pct': 0.00}
            }
        stats['budgets'][b.code]['before'] = {
                'value': b.sum_value,
                'pct': round(float(b.sum_value)/total*100, 2)
                }
        unknown_value_before -= b.sum_value
    for a in after:
        if a.code not in stats['budgets']:
            stats['budgets'][a.code] = {
                'code': util.nulltoDash(a.code),
                'name': util.nulltoUnknown(a.name),
                'before': {'value': 0.00, 'pct': 0.00
                }
            }
        stats['budgets'][a.code]['after'] = {
                'value': a.sum_value,
                'pct': round(float(a.sum_value)/total*100, 2)
                }
        unknown_value_after -= a.sum_value

    stats["budgets"]["-"] = {
        'code': '-',
        'name': "Unknown",
        'before': {
            'value': unknown_value_before,
            'pct': round(float(unknown_value_before)/total*100, 2)
        },
        'after': {
            'value': unknown_value_after,
            'pct': round(float(unknown_value_after)/total*100, 2)
        }
    }

    for code, budget in stats['budgets'].items():
        try:
            stats['budgets'][code]['change_pct'] = round(
            ((budget['after']['value']-budget['before']['value']
                ) / budget['before']['value']) * 100, 2)
        except ZeroDivisionError:
            stats['budgets'][code]['change_pct'] = "NEW"
            
        if stats['budgets'][code]['change_pct'] == 0.0:
            stats['budgets'][code]['change_pct'] = ""

        stats['budgets'][code]['before']['value'] = "{:,.2f}".format(stats['budgets'][code]['before']['value'])
        stats['budgets'][code]['after']['value'] = "{:,.2f}".format(stats['budgets'][code]['after']['value'])

    after.close()
    before.close()
    return stats
    
def get_colour(node, ccolours):
    if ccolours:
        if node in ccolours: return ccolours[node]
    return node

def country_project_stats(country_code):

    projects = abprojects.projects(country_code)
    total_projects = len(projects)
    total_value = sum(map(lambda project:
         util.none_is_zero(project.total_commitments), projects))
    return {
        "total_value": "{:,}".format(total_value),
        "total_projects": total_projects,
       }

def earliest_latest_disbursements(country_code):
    country = abprojects.country(country_code)
    MIN_MAX_FY_QUERY = """
    SELECT strftime('%%Y', MIN(DATE(transaction_date, '-%s month')))
    AS min_fiscal_year,
		strftime('%%Y', MAX(DATE(transaction_date, '-%s month')))
		    AS max_fiscal_year
    FROM atransaction
    JOIN activity ON
        activity.iati_identifier=atransaction.activity_iati_identifier
    JOIN recipientcountries ON
        recipientcountries.activity_iati_identifier = activity.iati_identifier
    WHERE recipientcountries.recipient_country_code = '%s'
    AND atransaction.transaction_type_code IN('%s')
    """
    fydata_results = db.engine.execute(MIN_MAX_FY_QUERY % (
            country.fiscalyear_modifier,
            country.fiscalyear_modifier, country_code, "D','E")
            ).first()
    return int(fydata_results.min_fiscal_year), int(fydata_results.max_fiscal_year)

def earliest_latest_forward_data(country_code):
    country = abprojects.country(country_code)
    MIN_MAX_FY_QUERY = """
    SELECT strftime('%%Y', MIN(DATE(period_start_date, '-%s month')))
    AS min_fiscal_year,
		strftime('%%Y', MAX(DATE(period_start_date, '-%s month')))
		    AS max_fiscal_year
    FROM forwardspend
    JOIN activity ON
        activity.iati_identifier=forwardspend.activity_iati_identifier
    JOIN recipientcountries ON
        recipientcountries.activity_iati_identifier = activity.iati_identifier
    WHERE recipientcountries.recipient_country_code = '%s'
    """
    fydata_results = db.engine.execute(MIN_MAX_FY_QUERY % (
            country.fiscalyear_modifier,
            country.fiscalyear_modifier, country_code)
            ).first()
    return int(fydata_results.min_fiscal_year), int(fydata_results.max_fiscal_year)

def sectors_stats():
    # for each sector, count number of projects and value using that
    #  sector.
    sql = """
    SELECT
    dacsector.code, dacsector.description_EN,
    dacsector.parent_code,
    group_concat(activity.recipient_country_code) AS countries,
    sum(atransaction.value*sector.percentage/100) AS sum_value,
    count(activity.id) AS num_activities
    FROM dacsector
    LEFT JOIN sector ON sector.code = dacsector.code
    LEFT JOIN activity ON
        activity.id = sector.activity_iati_identifier
    LEFT JOIN atransaction ON
        activity.id=atransaction.activity_iati_identifier
    WHERE sector.deleted = 0
    AND atransaction.transaction_type_code='C'
    GROUP BY dacsector.code
    ;"""
    sector_stats_results = db.engine.execute(sql)

    def tidy_countries(countries):
        return ",".join(set(countries.split(",")))

    stats = []
    for sector in sector_stats_results:
        stats.append({
            "sector_code": sector.code,
            "sector_description": sector.description_EN,
            "sector_parent_code": sector.parent_code,
            "countries": tidy_countries(sector.countries),
            "total_value": round(sector.sum_value, 2),
            "num_activities": sector.num_activities
        })
    return stats
