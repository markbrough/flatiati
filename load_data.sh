#!/bin/bash
./abtool.py --setup
# Senegal - Canada and UNDP
./abtool.py --import --filename="data/senegal/xml/CA-3-SN.xml" --country-code="SN" --sample
./abtool.py --update-projects --filename="data/senegal/xls/canada.xls" --country-code="SN" --reporting-org="CA-3"
./abtool.py --import --filename="data/senegal/xml/undp-sn.xml" --country-code="SN"
./abtool.py --update-projects --filename="data/senegal/xls/undp.xls" --country-code="SN" --reporting-org="41114"
./abtool.py --import-budget --filename="data/senegal/senegal_CC_budget.csv" --country-code="SN" --budget-type="f"
# -- end Senegal
# Nepal - DFID
./abtool.py --import --filename="data/nepal/xml/dfid-np.xml" --country-code="NP"
./abtool.py --update-projects --filename="data/nepal/xls/GB-1-NP-new.xls" --country-code="SN" --reporting-org="GB-1"
./abtool.py --import-budget --filename="data/nepal/nepal_CC_functional.csv" --country-code="NP" --budget-type="f"
./abtool.py --import-budget --filename="data/nepal/nepal_CC_admin.csv" --country-code="NP" --budget-type="a"
# -- end Nepal
# Haiti - Canada and WB
./abtool.py --import --filename="data/haiti/xml/CA-3-HT.xml" --country-code="HT"
./abtool.py --update-projects --filename="data/haiti/xls/canada-HT.XLS" --reporting-org="CA-3" --country-code="HT"
./abtool.py --import --filename="data/haiti/xml/worldbank-ht.xml" --country-code="HT"
# Missing WB Excel file
./abtool.py --import-budget --filename="data/haiti/haiti-mapping.csv" --country-code="HT" --budget-type="f"
# -- end Haiti
# Moldova - USAID
./abtool.py --import --filename="data/moldova/xml/US-1-md.xml" --country-code="MD"
./abtool.py --update-projects --filename="data/moldova/xls/US-1-new.xls" --reporting-org="US-1" --country-code="MD"
./abtool.py --import-budget --filename="data/moldova/moldova_CC_functional.csv" --country-code="MD" --budget-type="f"
./abtool.py --import-budget --filename="data/moldova/moldova_CC_admin.csv" --country-code="MD" --budget-type="a"
# Remember to manually adjust Fiscal Years for each country!
