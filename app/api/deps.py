from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import InvalidTokenError
from app.models.user import User
from app.services import auth as auth_service

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    user_id = auth_service.verify_access_token(credentials.credentials)
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise InvalidTokenError()
    return user
