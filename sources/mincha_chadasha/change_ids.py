import django
django.setup()
from sefaria.system.database import db

sheets = db.sheets.find({'owner': 270678})
for i, sheet in enumerate(sheets):
    new_id = 728000 + i
    db.sheets.update_one(
        {'_id': sheet['_id']},
        {'$set': {'id': new_id}}
    )

