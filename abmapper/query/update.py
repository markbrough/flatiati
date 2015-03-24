#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abmapper import app, db
from abmapper.lib import util
from abmapper.query import models
from abmapper.query import projects as abprojects
from abmapper.query import sectors as absectors
import unicodecsv
import xlrd

def deleted_sector_codes_from_cc(deleted_ccs, project_sectors):
    def filterer(project_sector):
        return (project_sector.dacsector.cc_id in deleted_ccs
                                ) and (project_sector.deleted==False)
    return filter(filterer, project_sectors)

def get_num_sectors(sheet, i):
    num_sectors = 1
    for checkrow in range(i+1, sheet.nrows):
        if sheet.cell_type(checkrow, 0)==0:
            num_sectors+=1
        if sheet.cell_type(checkrow, 0)==1:
            break
    return num_sectors

def get_sectors(sheet, i, num_sectors):
    sectors = []
    for si in range(i, i+num_sectors):
        sectors.append(
            {
    "crs_code": util.correct_trailing_decimals(
                    sheet.cell(si, 3).value),
    "cc_id": util.correct_zeros(
                    sheet.cell(si, 6).value),
    "percentage": "UNKNOWN",
            }
        )
    return sectors

def _get_project_data(project_data, sheet, i):
    # Start collecting project data
    project_id = sheet.cell(i, 0).value
    capital_spend = util.number_or_none(sheet.cell(i, 14).value)

    num_sectors = get_num_sectors(sheet, i)
    project_data[project_id] = {
        'capital_spend': capital_spend,
        'num_sectors': num_sectors,
        'sectors': get_sectors(sheet, i, num_sectors)
    }
    return project_data
  
def get_project_data(sheet):
    project_data = {}
    for i in range(1, sheet.nrows):
        if sheet.cell_type(i, 0)==1:
            project_data = _get_project_data(project_data,
                                sheet, i)
        # End collecting project data
        if sheet.cell_type(i, 0)==0: 
            continue
    return project_data

def get_added_deleted_sectors(sheet_sectors, db_sectors):
    # Compare sheet sectors with db sectors
    #   For each sector in the db, check if the sheet sectors have a 
    #   different CC
    
    new_sectors = dict(map(lambda s: (
             s["crs_code"],
             {
             'percentage': s["percentage"],
             'cc_id': s["cc_id"]}
             ), sheet_sectors))

    existing_sectors = dict(map(lambda s: (
            s.code, 
            {
            'percentage': s.percentage,
            'cc_id': s.dacsector.cc_id,
            'deleted': s.deleted
            }
            ), db_sectors))
    
    changed_sectors = {}
    
    for sector_code, es in existing_sectors.items():
        # This should break if the sector codes have changed
        try:
            assert sector_code in new_sectors
        except AssertionError:
            print "Sector code %s not found in spreadsheet"
            raise
        
        ns = new_sectors[sector_code]
        
        # Set CC ID to spreadsheet input CC ID; set percentage to
        # database pct value
        if es['cc_id'] != ns['cc_id']:
            changed_sectors[sector_code] = {
                "cc_id": ns['cc_id'],
                "percentage": es["percentage"]
            }
    return changed_sectors

def update_capital_exp(p, capital_spend):
    # Update capital expenditure
    p.capital_exp = capital_spend
    db.session.add(p)
    db.session.commit()

def handle_changed_sectors(changed_sectors, project_identifier):

    # 1 Find sectors related to deleted CCs for this project
    #   Try and match them against existing CCs
    
    for sector_code, cs_data in changed_sectors.items():
        
        # Delete old sector with that CRS code
        # Add a new one, using the old CRS code as the formersector_id
        
        new_cc_id = cs_data['cc_id']
        percentage = cs_data['percentage']
        newsector_code = absectors.get_sector_from_cc(new_cc_id)
        
        formersector_id = absectors.delete_sector_from_project(
                sector_code,
                project_identifier)
        
        absectors.add_sector_to_project(newsector_code, 
                              project_identifier, 
                              percentage, 
                              formersector_id, 
                              True)

        print "Updated sector for project %s, with sector code %s \
and CC id %s" % (project_identifier, newsector_code, new_cc_id)

def update_project(project_identifier, sectors):
    p = abprojects.project(project_identifier)
    if not p:
        print "UNKNOWN PROJECT", project_identifier
        return

    changed_sectors = get_added_deleted_sectors(
        sectors["sectors"],
        p.sectors)

    update_capital_exp(p, sectors["capital_spend"])
    
    if changed_sectors:
        handle_changed_sectors(changed_sectors,
                                    project_identifier)

def update_projects(data):
    f = data.filename
    print "Trying to read %s" % f
    sheetname = "Raw data export"
    book = xlrd.open_workbook(filename=f)
    sheet = book.sheet_by_name(sheetname)
    project_data = get_project_data(sheet)

    # For each project
    for project_identifier, sectors in project_data.items():
        update_project(project_identifier, sectors)