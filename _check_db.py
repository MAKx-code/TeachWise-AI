from app import create_app, db
from sqlalchemy import inspect as sa_inspect
app = create_app()
with app.app_context():
    tables = sa_inspect(db.engine).get_table_names()
    print(f'Tables created: {len(tables)}')
    for t in sorted(tables):
        print(f'  {t}')
