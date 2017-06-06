#!/usr/bin/env python

# Takes IATI-XML with hierarchy, and flattens based on flatten_rules

import optparse, sys
from lxml import etree
import os, datetime
import flatten_rules

def get_root(doc):
    import copy
    newdoc = copy.deepcopy(doc)
    if type(newdoc) == etree._ElementTree:
        newdoc = newdoc.getroot()
    for e in newdoc:
        newdoc.remove(e)
    return newdoc

def get_reporting_org_activities(rep, root, doc):
    data = {}
    
    print flatten_rules.FLATTEN_RULES
    rules = flatten_rules.FLATTEN_RULES[rep]
    
    # Get all hierarchies
    hierarchies = set(doc.xpath(('//iati-activity[reporting-org/@ref="{}"]/@hierarchy'.format(rep))))
    for h in hierarchies:
        data[h] = {}
        rep_h_acts = doc.xpath(('//iati-activity[reporting-org/@ref="{}"][@hierarchy="{}"]'.format(rep, h)))
        for a in rep_h_acts:
            data[h][a.find('iati-identifier').text] = a
    
    # If flattening down, we are looking for the child of this parent
    # If flattening up, we are looking for the parent of this child
    # IATI codelists: 1 = Parent relation; 2 = Child relation
    related_activity_type = {True: "2", False: "1"}[rules["flatten_down"]]
    related_activity_h = {True: 1, False: -1}[rules["flatten_down"]]
    
    for from_h in sorted(rules["flatten_from"], reverse=rules["flatten_down"]):
        for iati_id, activity in data[from_h].items():
            related_activity_ids = activity.xpath(
                'related-activity[@type="{}"]/@ref'.format(related_activity_type))
            if not related_activity_ids: 
                continue
            other_activity = data[str(int(from_h)+related_activity_h)].get(related_activity_ids[0])
            if not other_activity:
                continue
            
            for element in rules["flatten_from_fields"][from_h]:
                for el in activity.xpath(element):
                    other_activity.append(el)

    for iati_id, activity in data[rules["flatten_to"]].items():
        root.append(activity)
    return rep, root

def generate_flattened_xml(doc):
    """Accepts an lxml.ElementTree object"""
    root = get_root(doc)
    reporting_orgs = set(doc.xpath('//reporting-org/@ref'))

    return dict([get_reporting_org_activities(ro, root, doc
                    ) for ro in reporting_orgs])

def flatten(doc):
    return generate_flattened_xml(doc)

if __name__ == '__main__':
    main()