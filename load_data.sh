#!/bin/bash
./abtool.py --setup
./abtool.py --import --filename="data/senegal/xml/CA-3-SN.xml" --country-code="SN" --sample
./abtool.py --update-projects --filename="data/senegal/xls/canada.xls" --country-code="SN" --reporting-org="CA-3"
./abtool.py --import-budget --filename="data/senegal/senegal_CC_budget.csv" --country-code="SN" --budget-type="f"

./abtool.py --import --filename="data/senegal/xml/undp-sn.xml" --country-code="SN"
./abtool.py --update-projects --filename="data/senegal/xls/undp.xls" --country-code="SN" --reporting-org="41114"

./abtool.py --import --filename="data/nepal/xml/dfid-np.xml" --country-code="NP"
./abtool.py --update-projects --filename="data/nepal/xls/GB-1-NP-new.xls" --country-code="SN" --reporting-org="GB-1"