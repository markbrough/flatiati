#!/usr/bin/env python
# -*- coding: utf-8 -*-

from abmapper import app, db
from abmapper.query import models
import unicodecsv

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
            raise BudgetSetupError("Didn't recognise country or budget \
                                    type, or both")

        c.budgettype_id = budget_type
        db.session.add(c)
        db.session.commit()

    setup_budget_type(budget_type, country_code)

    # Do we want to wipe the slate clean? Remove all budget codes for this
    # country?

    # Add new high and low level sectors, if they exist, and add links
    # with CC
    for row in budgetcsv:
        cc_id = row["CC"]
        budget_code = row["BUDGET_CODE"]
        budget_name = row["BUDGET_NAME"]
        low_budget_code = row["LOWER_BUDGET_CODE"]
        low_budget_name = row["LOWER_BUDGET_NAME"]
    
        if budget_code != "":
            budget_code_id = add_budget_code(country_code, budget_type,
                             cc_id, budget_code, budget_name)
            if low_budget_code != "":
                add_low_budget_code(country_code, budget_type, cc_id,
                        budget_code_id, low_budget_code, low_budget_name)

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
            print "Sorry, this CC is already associated with another \
                   budget code for the same country"
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

    def add_code(country_code, low_budget_code, low_budget_name,
                 budget_type, budget_code):
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
            print "Sorry, this CC is already associated with another \
                   budget code for the same country"
            return False
        
        bcl = models.CCLowerBudgetCode()
        bcl.cc_id = cc_id
        bcl.lowerbudgetcode_id = bc.id
        db.session.add(bcl)
        db.session.commit()
        return bcl                        

    bc = add_code(country_code, low_budget_code, low_budget_name,
                  budget_type, budget_code)

    add_link(country_code, bc, cc_id)