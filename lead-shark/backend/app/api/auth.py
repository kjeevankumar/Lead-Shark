from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import User
from app.schemas.schemas import UserLogin, UserCreate, UserResponse, Token
from app.core.security import verify_password, get_password_hash, create_access_token, get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Authentication"])

class RoleSwitchRequest(BaseModel):
    role: str # admin, reviewer, sales

@router.post("/login", response_model=Token)
def login(creds: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == creds.email).first()
    if not user or not verify_password(creds.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User account is deactivated")
        
    access_token = create_access_token(data={"sub": user.email, "role": user.role, "name": user.full_name})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/switch-demo-role", response_model=Token)
def switch_demo_role(req: RoleSwitchRequest, db: Session = Depends(get_db)):
    """Allows demo evaluators to switch roles smoothly between Admin, Reviewer, and Sales"""
    valid_roles = ["admin", "reviewer", "sales"]
    target_role = req.role.lower()
    if target_role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Choose from: {valid_roles}")
        
    email = f"{target_role}@leadshark.io"
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Create demo user on the fly if needed
        user = User(
            email=email,
            hashed_password=get_password_hash("LeadShark2026!"),
            full_name=f"{target_role.capitalize()} Operator",
            role=target_role
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
    access_token = create_access_token(data={"sub": user.email, "role": user.role, "name": user.full_name})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }
