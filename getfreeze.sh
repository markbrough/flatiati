source ./pyenv/bin/activate
mkdir abmapper/build
cd abmapper/build
git init .
git remote add origin git@github.com:markbrough/flatiati.git
git fetch origin gh-pages
git checkout gh-pages
rm -rf en fr index.html static CNAME
cd ../../
./abtool.py --update-exchange-rates
./abtool.py --update-all
./manage.py freeze
cd abmapper/build
git init .
echo "spreadsheets.aidonbudget.org" > CNAME
git add .
git commit -a -m "Update"
git push origin gh-pages