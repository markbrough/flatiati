FlatIATI
========

Retrieves IATI data and makes it downloadable as beautiful spreadsheets.

License: AGPL v3.0
------------------

Copyright (C) 2017 Mark Brough, Overseas Development Institute

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

What the tool does 
------------------
1. Retrieves data from the IATI Datastore
2. Reads data in version 1.x and 2.x of the IATI Standard
3. Converts all currencies to USD
4. Flattens hierarchies in publishers' data
5. Allows data to be exported in English and French.

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
