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
        return a[0] not in dict(b).keys()
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
    return value

def correct_trailing_decimals(value):
    try:
        return int(value)
    except TypeError:
        return value

def filter_none_out(proj):
    return proj.capital_exp is not None

def filter_none_in(proj):
    return proj.capital_exp is None

class BudgetSetupError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def import_budget(data):
    f = data.filename
    print "Trying to read %s" % f
    budgetcsv = unicodecsv.DictReader(open(f))

    budget_type = data.budget_type
    country_code = data.country_code

    # Setup budget type
    def setup_budget_type(budget_type, country_code):
        bt = models.BudgetType.query.filter_by(
                code=budget_type
            ).first()
        c = models.RecipientCountry.query.filter_by(
                code=country_code
            ).first()
        if not c or not bt:
            raise BudgetSetupError("Didn't recognise country or budget type, or both")

        c.budgettype_id = budget_type
        db.session.add(c)
        db.session.commit()

    setup_budget_type(budget_type, country_code)

    # Do we want to wipe the slate clean? Remove all budget codes for this country?

    # Add new high and low level sectors, if they exist, and add links with CC
    for row in budgetcsv:
        cc_id = row["CC"]
        budget_code = row["BUDGET_CODE"]
        budget_name = row["BUDGET_NAME"]
        low_budget_code = row["LOWER_BUDGET_CODE"]
        low_budget_name = row["LOWER_BUDGET_NAME"]
    
        if budget_code != "":
            budget_code_id = add_budget_code(country_code, budget_type, cc_id, 
                        budget_code, budget_name)
            if low_budget_code != "":
                add_low_budget_code(country_code, budget_type, cc_id, budget_code_id, 
                            low_budget_code, low_budget_name)

def add_budget_code(country_code, budget_type, cc_id, budget_code, 
                        budget_name):
    print country_code
    print "Adding budget code"

    def add_code(country_code, budget_code, budget_name, budget_type):
        # Check if this budget code already exists
        checkBC = models.BudgetCode.query.filter_by(
                    country_code = country_code,
                    code = budget_code
                  ).first()
        if checkBC:
            print "This budget code already exists"
            return checkBC
    
        bc = models.BudgetCode()
        bc.country_code = country_code
        bc.code = budget_code
        bc.name = budget_name
        bc.budgettype_code = budget_type
        db.session.add(bc)
        db.session.commit()
        return bc

    def add_link(country_code, bc, cc_id):
        # Check this CC is not related to another code for this country

        checkBCL = db.session.query(models.CCBudgetCode,
                                    models.BudgetCode
                   ).filter(
                        models.BudgetCode.country_code == country_code,
                        models.CCBudgetCode.cc_id == cc_id
                   ).join(models.BudgetCode
                   ).first()
        if checkBCL:
            print "Sorry, this CC is already associated with another budget \
                   code for the same country"
            return False
        
        bcl = models.CCBudgetCode()
        bcl.cc_id = cc_id
        bcl.budgetcode_id = bc.id
        db.session.add(bcl)
        db.session.commit()
        return bcl                        

    bc = add_code(country_code, budget_code, budget_name, budget_type)

    add_link(country_code, bc, cc_id)

    return bc.id    

def add_low_budget_code(country_code, budget_type, cc_id, budget_code, 
                            low_budget_code, low_budget_name):
    print country_code
    print "Adding low budget code"

    def add_code(country_code, low_budget_code, low_budget_name, budget_type,
                            budget_code):
        # Check if this budget code already exists
        checkBC = models.LowerBudgetCode.query.filter_by(
                    country_code = country_code,
                    code = low_budget_code
                  ).first()
        if checkBC:
            print "This low budget code already exists"
            return checkBC
    
        bc = models.LowerBudgetCode()
        bc.country_code = country_code
        bc.code = low_budget_code
        bc.name = low_budget_name
        bc.budgettype_code = budget_type
        bc.parent_budgetcode_id = budget_code
        db.session.add(bc)
        db.session.commit()
        return bc

    def add_link(country_code, bc, cc_id):
        # Check this CC is not related to another code for this country

        checkBCL = db.session.query(models.CCLowerBudgetCode,
                                    models.LowerBudgetCode
                   ).filter(
                        models.LowerBudgetCode.country_code == country_code,
                        models.CCLowerBudgetCode.cc_id == cc_id
                   ).join(models.LowerBudgetCode
                   ).first()
        if checkBCL:
            print "Sorry, this CC is already associated with another budget \
                   code for the same country"
            return False
        
        bcl = models.CCLowerBudgetCode()
        bcl.cc_id = cc_id
        bcl.lowerbudgetcode_id = bc.id
        db.session.add(bcl)
        db.session.commit()
        return bcl                        

    bc = add_code(country_code, low_budget_code, low_budget_name, budget_type, 
                  budget_code)

    add_link(country_code, bc, cc_id)

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
            capital_spend = number_or_none(sheet.cell(i, 14).value)

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
                    "crs_code": correct_trailing_decimals(sheet.cell(si, 3).value),
                    "cc_id": correct_zeros(sheet.cell(si, 6).value),
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

        new_sectors = map(lambda s: (s["cc_id"], {'percentage': s["percentage"], 
                                                       'original_crs_code': s["crs_code"]}), 
                                                            sectors['sectors'])

        existing_sectors = map(lambda s: (s.dacsector.cc_id, {
                                                'percentage': s.percentage,
                                                'original_crs_code': s.code,
                                                'deleted': s.deleted}),
                                                            p.sectors)

        added_sectors = a_not_in_b(new_sectors, existing_sectors)
        deleted_sectors = a_not_in_b(existing_sectors, new_sectors)

        added_sectors = dict(map(lambda s: (s[1]['original_crs_code'], {
                                                'percentage': s[1]['percentage'],
                                                'cc_id': s[0]}),
                                                    added_sectors))

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
            #   Try and match them against existing CCs
            
            for ds in deleted_sectors:

                # For each sector that needs to be deleted...
                sector_to_delete_cc_id = ds[0]
                sector_to_delete = ds[1]

                original_crs_code = sector_to_delete['original_crs_code']
                percentage = sector_to_delete['percentage']

                print "Deleting CC ID:", sector_to_delete_cc_id
                print "Had CRS code, pct:", original_crs_code, percentage

                newsector_code = False

                try:
                    new_cc_id = added_sectors[original_crs_code]['cc_id']
                    newsector_code = get_sector_from_cc(new_cc_id)
                    added_sectors.pop(original_crs_code)
                except KeyError:
                    print "WARNING: Couldn't find CRS CODE", original_crs_code, "for project", project_id


                formersector_id = delete_sector_from_project(original_crs_code, 
                                                             project_identifier)

                print "Deleting sector for", project_identifier, original_crs_code

                if not newsector_code:
                    continue
                
                add_sector_to_project(newsector_code, 
                                      project_identifier, 
                                      percentage, 
                                      formersector_id, 
                                      True)

                print "Adding sector for", project_identifier, newsector_code, percentage, formersector_id
            
        # Check if there are any remaining unadded sectors.
        if added_sectors:
            print "Remaining sectors to add", len(added_sectors)
            print added_sectors
            # 3 Get pct of remaining percentage
            unused_sector_pct = get_unused_sector_percentage(project_identifier)

            # 4 Set default percentage value for new added sectors (divide total
            # available amount by number of added sectors)

            default_sector_pct = float(unused_sector_pct)/len(added_sectors)

            if default_sector_pct<=0: print "ALERT: 0 VALUE SECTORS"


            for crscode, addsector in added_sectors.items():
                # 5 Get a random sector associated with this CC
                newsector_code = get_sector_from_cc(addsector['cc_id'])
                if not newsector_code:
                    print "UNRECOGNISED CC ID", addsector
                    continue
                print "New sector is", addsector

                # 6 Add that sector to the project, but mark it as assumed

                def getRelevantSector(sector):
                    return sector["cc_id"] == addsector['cc_id']

                relevant_sector = get_first(filter(getRelevantSector, sectors['sectors']))
                if is_number(relevant_sector["percentage"]):
                    percentage = relevant_sector["percentage"]
                else:
                    percentage = default_sector_pct

                add_sector_to_project(newsector_code, project_identifier, percentage, None, True)
        
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

def add_sector_to_project(sector_code, iati_identifier, percentage, 
                          formersector_id=None, assumed=False):
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
    newS.formersector_id = formersector_id
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

def budget_project_stats(country_code):
    sql = """SELECT sum(atransaction.value*sector.percentage/100) AS sum_value,
            budgetcode.code, budgetcode.name
            FROM atransaction
            JOIN activity ON activity.iati_identifier=atransaction.activity_iati_identifier
            JOIN sector ON activity.iati_identifier = sector.activity_iati_identifier
            LEFT JOIN dacsector ON sector.code = dacsector.code
            LEFT JOIN commoncode ON dacsector.cc_id = commoncode.id
            LEFT JOIN ccbudgetcode ON commoncode.id = ccbudgetcode.cc_id
            LEFT JOIN budgetcode ON ccbudgetcode.budgetcode_id = budgetcode.id
            WHERE sector.deleted = 0
            AND activity.recipient_country_code="%s"
            AND activity.aid_type_code IN ('C01', 'D01', 'D02')
            AND activity.status_code IN (2, 3)
            AND atransaction.transaction_type_code="C"
            GROUP BY budgetcode.code
            ;"""

    sql_before = """SELECT sum(atransaction.value*sector.percentage/100) AS sum_value,
            budgetcode.code, budgetcode.name
            FROM atransaction
            JOIN activity ON activity.iati_identifier=atransaction.activity_iati_identifier
            JOIN sector ON activity.iati_identifier = sector.activity_iati_identifier
            LEFT JOIN dacsector ON sector.code = dacsector.code
            LEFT JOIN commoncode ON dacsector.cc_id = commoncode.id
            LEFT JOIN ccbudgetcode ON commoncode.id = ccbudgetcode.cc_id
            LEFT JOIN budgetcode ON ccbudgetcode.budgetcode_id = budgetcode.id
            WHERE sector.edited = 0
            AND activity.recipient_country_code="%s"
            AND activity.aid_type_code IN ('C01', 'D01', 'D02')
            AND activity.status_code IN (2, 3)
            AND atransaction.transaction_type_code="C"
            GROUP BY budgetcode.code
            ;"""


    sql_total = """SELECT sum(atransaction.value*sector.percentage/100) AS sum_value,
            budgetcode.code, budgetcode.name
            FROM atransaction
            JOIN activity ON activity.iati_identifier=atransaction.activity_iati_identifier
            JOIN sector ON activity.iati_identifier = sector.activity_iati_identifier
            LEFT JOIN dacsector ON sector.code = dacsector.code
            LEFT JOIN commoncode ON dacsector.cc_id = commoncode.id
            LEFT JOIN ccbudgetcode ON commoncode.id = ccbudgetcode.cc_id
            LEFT JOIN budgetcode ON ccbudgetcode.budgetcode_id = budgetcode.id
            WHERE sector.deleted = 0
            AND activity.recipient_country_code="%s"
            AND activity.aid_type_code IN ('C01', 'D01', 'D02')
            AND activity.status_code IN (2, 3)
            AND atransaction.transaction_type_code="C"
            ;"""

    after = db.engine.execute(sql % country_code)
    before = db.engine.execute(sql_before % country_code)
    total = db.engine.execute(sql_total % country_code).first()[0]

    stats = {'total': total,
             'budgets': {}}
    for b in before:
        if b.code not in stats['budgets']:
            stats['budgets'][b.code] = {'code': b.code,
                                        'name': b.name,
                                        'after': {'value': 0.00, 'pct': 0.00}}
        stats['budgets'][b.code]['before'] = {
                'value': b.sum_value,
                'pct': round(float(b.sum_value)/total*100, 2)
                }
    for a in after:
        if a.code not in stats['budgets']:
            stats['budgets'][a.code] = {'code': a.code,
                                        'name': a.name,
                                        'before': {'value': 0.00, 'pct': 0.00}
                                        }
        stats['budgets'][a.code]['after'] = {
                'value': a.sum_value,
                'pct': round(float(a.sum_value)/total*100, 2)
                }

    for code, budget in stats['budgets'].items():
        try:
            stats['budgets'][code]['change_pct'] = round(((budget['after']['value']-budget['before']['value'])/budget['before']['value'])*100, 2)
        except ZeroDivisionError:
            stats['budgets'][code]['change_pct'] = "NEW"
            
        if stats['budgets'][code]['change_pct'] == 0.0:
            stats['budgets'][code]['change_pct'] = ""

        stats['budgets'][code]['before']['value'] = "{:,.2f}".format(stats['budgets'][code]['before']['value'])
        stats['budgets'][code]['after']['value'] = "{:,.2f}".format(stats['budgets'][code]['after']['value'])


    after.close()
    before.close()
 
    return stats

def country_project_stats(country_code, aid_types=["C01", "D01", "D02"], 
                                        activity_statuses=[2,3]):

    original_p = projects(country_code)

    total_projects = len(original_p)

    def aid_type_filter(the_project):
        return (the_project.aid_type_code in aid_types) and (
                    the_project.status_code in activity_statuses)

    p = filter(aid_type_filter, original_p)

    filtered_projects = len(p)

    total_value = sum(map(lambda project: none_is_zero(project.total_commitments), original_p))
    total_filtered_value = sum(map(lambda project: none_is_zero(project.total_commitments), p))
    total_mappable_before = sum(map(lambda project: none_is_zero(project.pct_mappable_before)/100 * 
                none_is_zero(project.total_commitments), p))
    total_mappable_after = sum(map(lambda project: none_is_zero(project.pct_mappable_after)/100 * 
                none_is_zero(project.total_commitments), p))
    total_capital_before = 0.00
    total_capital_after = sum(map(lambda project: project.capital_exp * 
                none_is_zero(project.total_commitments), filter(filter_none_out, p)))
    total_na_after = sum(map(lambda project: 1 * 
                none_is_zero(project.total_commitments), filter(filter_none_in, p)))
    total_current_after = total_filtered_value-total_capital_after-total_na_after
    return {"total_value": "{:,}".format(total_value),
            "total_filtered_value": "{:,}".format(total_filtered_value),
            "total_mappable_before": total_mappable_before,
            "total_mappable_before_pct": round(total_mappable_before/total_filtered_value*100, 2),
            "total_mappable_after": total_mappable_after,
            "total_mappable_after_pct": round(total_mappable_after/total_filtered_value*100, 2),
            "total_capital_before_pct": round(total_capital_before/total_filtered_value*100, 2),
            "total_capital_after_pct": round(total_capital_after/total_filtered_value*100, 2),
            "total_current_after_pct": round(total_current_after/total_filtered_value*100, 2),
            "total_projects": total_projects,
            "filtered_projects": filtered_projects,
           }
