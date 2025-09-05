from typing import Optional, Any, Type, TypeVar
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import logging

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType")


class SecurityError(Exception):
    pass


class BaseRepository:
    def __init__(self, db_session: Session, model_class: Type[ModelType]):
        self.db = db_session
        self.model_class = model_class
        
        # SQL injection koruması için yasaklı kelimeler
        self.forbidden_keywords = {
            'union', 'select', 'insert', 'update', 'delete', 'drop', 'alter',
            'create', 'exec', 'execute', 'sp_', 'xp_', '--', ';', '/*', '*/',
            'script', 'javascript', 'vbscript', 'onload', 'onerror',
            ' or '
        }

    def _validate_field_name(self, field_name: str) -> str:
        """Field adını validate et"""
        if not field_name or not isinstance(field_name, str):
            raise SecurityError(f"Invalid field name: {field_name}")
        
        # Sadece alphanumeric ve underscore
        if not field_name.replace('_', '').replace('.', '').isalnum():
            raise SecurityError(f"Invalid characters in field name: {field_name}")
        
        # Yasaklı kelime kontrolü
        field_lower = field_name.lower()
        for keyword in self.forbidden_keywords:
            if keyword in field_lower:
                raise SecurityError(f"Forbidden keyword in field name: {field_name}")
        
        return field_name
    
    def _validate_value(self, value: Any) -> Any:
        """Değeri validate et"""
        if isinstance(value, str):
            # String SQL injection kontrolü
            value_lower = value.lower()
            for keyword in self.forbidden_keywords:
                if keyword in value_lower:
                    raise SecurityError(f"Forbidden keyword in value: {value}")
        
        return value

    def find_by_id(self, id_value: Any, include_deleted: bool = False) -> Optional[ModelType]:
        query = self.db.query(self.model_class).filter(self.model_class.id == id_value)
        if hasattr(self.model_class, "is_deleted") and not include_deleted:
            query = query.filter(self.model_class.is_deleted.is_(False))
        return query.first()

    def create(self, **kwargs) -> ModelType:
        try:
            valid = {k: self._validate_value(v) for k, v in kwargs.items() if hasattr(self.model_class, k)}
            instance = self.model_class(**valid)
            self.db.add(instance)
            self.db.flush()
            return instance
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Integrity error in create: {e}")
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error in create: {e}")
            raise


class RepositoryFactory:
    def __init__(self, db_session: Session):
        self.db = db_session

    def get_base_repository(self, model_class: Type[ModelType]) -> BaseRepository:
        return BaseRepository(self.db, model_class)


__all__ = ["BaseRepository", "RepositoryFactory", "SecurityError"]
