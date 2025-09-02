from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# Oturumların commit sonrasında boşalmaması için expire_on_commit=False
# kullanılır. Testlerde nesnelerin oturum dışında da kullanılabilmesi için
# önemlidir.
db = SQLAlchemy(session_options={"expire_on_commit": False})
migrate = Migrate()
