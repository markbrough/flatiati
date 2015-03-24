Aid-Budget Mapper
=================

Maps aid data published by donors in the IATI format to country budget classifications.

License: AGPL v3.0
------------------

Copyright (C) 2015 Mark Brough, Publish What You Fund

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

Installation
------------

Set up a virtualenv:

    virtualenv ./pyenv

Activate the virtualenv:

    source ./pyenv/bin/activate

Install the requirements:

    pip install -r requirements.txt

Copy and edit the config.py.tmpl:

    cp config.py.tmpl config.py

Setup the database:

    ./abtool.py --setup

Run the server:

    python manage.py runserver

Importing files for a country
-----------------------------

Importing a file can also be done via `abtool.py`:

    ./abtool.py --import --filename="CA-3-SN.xml" --country-code="SN"

Importing a budget
------------------

Budgets map between the Common Code and the relevant country's budget
classification. They should be in CSV format and look like this:

| CC | BUDGET_CODE | BUDGET_NAME | LOWER_BUDGET_CODE | LOWER_BUDGET_NAME |
| --- | ----------- | ----------- | ----------------- | ----------------- |
| 1.1.1 | 11 | Organes exécutifs | 110 | Aff générales Présidence de la république |
| 1.2.1 | 10 | Organes législatifs | | |

NB ´LOWER_BUDGET_CODE` and `LOWER_BUDGET_NAME` are optional.

You can see an example of this in the 
[Senegal template file](abmapper/lib/senegal_CC_budget.csv)

You can then import the file with `abtool.py`:

    ./abtool.py --import-budget --filename="abmapper/lib/senegal_CC_budget.csv" --country-code="SN" --budget-type="f"
 
Where `budget-type` is `a` for administrative or `f` for functional
classification.