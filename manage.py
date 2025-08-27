import os
os.environ.setdefault("PYTHONPATH",".")
from importlib import import_module

flask_app_str = "backend:create_app"
mod_name, _, obj_name = flask_app_str.partition(":")
mod = import_module(mod_name)
app = getattr(mod, obj_name)() if (obj_name and hasattr(mod, obj_name) and callable(getattr(mod, obj_name))) else getattr(mod, obj_name or "app")

db = None
try:
    dbmod = ""
    if dbmod:
        db = import_module(dbmod).db
except Exception:
    pass

try:
    if db:
        from flask_migrate import Migrate
        Migrate(app, db)
except Exception:
    pass

if __name__ == "__main__":
    app.run()
