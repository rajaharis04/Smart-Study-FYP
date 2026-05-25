"""Auth API router — login & email verification/password setup with OTP."""
from datetime import datetime, timedelta
import random
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import User
from app.schemas.schemas import (
    LoginRequest, TokenResponse, ChangePasswordRequest,
    VerifyEmailRequest, VerifyEmailResponse, SetupPasswordRequest,
    SendOtpRequest, VerifyOtpRequest
)
from app.services.auth_service import verify_password, create_access_token, hash_password
from app.services.email_service import send_otp_email
from app.core.deps import get_current_admin

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    print(f"DEBUG: Received login request for email={request.email}")
    try:
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            print("DEBUG: User not found in DB")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        if not user.hashed_password:
            print("DEBUG: User has no password set (hashed_password is NULL)")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        if not verify_password(request.password, user.hashed_password):
            print("DEBUG: Password verification failed")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        if user.role != "admin" and user.role != "teacher" and user.role != "student":
            print(f"DEBUG: Access denied. Invalid role={user.role}")
            raise HTTPException(status_code=403, detail="Access denied.")

        if not user.is_active:
            print("DEBUG: Account is deactivated")
            raise HTTPException(status_code=403, detail="Account is deactivated.")

        token = create_access_token({"sub": str(user.id), "role": user.role})
        print("DEBUG: Login successful! Token generated.")
        return TokenResponse(
            access_token=token,
            role=user.role,
            full_name=user.full_name,
            must_change_password=user.must_change_password,
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"DEBUG: Unexpected error in login: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify-email", response_model=VerifyEmailResponse)
def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not registered in the system."
        )

    return VerifyEmailResponse(
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        has_password=user.hashed_password is not None,
        message="Email verified successfully."
    )


@router.post("/send-otp")
def send_otp(request: SendOtpRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not registered in the system."
        )

    # Generate 6-digit numeric OTP
    otp = f"{random.randint(100000, 999999)}"
    
    # Store OTP
    user.otp_code = otp
    user.otp_created_at = datetime.utcnow()
    db.commit()

    # Send real email using SMTP service
    send_otp_email(user.email, otp)

    return {"message": "OTP has been sent to your email."}


@router.post("/verify-otp")
def verify_otp(request: VerifyOtpRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not user.otp_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP."
        )

    # Check expiration (5 minutes)
    expiry_time = user.otp_created_at + timedelta(minutes=5)
    if datetime.utcnow() > expiry_time:
        user.otp_code = None
        user.otp_created_at = None
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired. Please request a new one."
        )

    if user.otp_code != request.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP code."
        )

    return {"message": "OTP verified successfully."}


@router.post("/setup-password")
def setup_password(request: SetupPasswordRequest, db: Session = Depends(get_db)):
    print(f"DEBUG: Received setup_password for email={request.email}, otp={request.otp}")
    try:
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            print("DEBUG: User not found in DB")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        # Validate OTP first
        if not user.otp_code or user.otp_code != request.otp:
            print(f"DEBUG: OTP mismatch. DB={user.otp_code}, Input={request.otp}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or missing OTP code. Cannot setup password."
            )

        # Check expiration (5 minutes)
        expiry_time = user.otp_created_at + timedelta(minutes=5)
        if datetime.utcnow() > expiry_time:
            print("DEBUG: OTP has expired")
            user.otp_code = None
            user.otp_created_at = None
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired. Please request a new one."
            )

        # Hash and save password, clear OTP fields
        user.hashed_password = hash_password(request.password)
        user.must_change_password = False
        user.otp_code = None
        user.otp_created_at = None
        db.commit()
        print("DEBUG: Password setup completed successfully!")

        return {"message": "Password set successfully. You can now log in."}
    except HTTPException:
        raise
    except Exception as e:
        print(f"DEBUG: Unexpected error in setup_password: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/change-password")
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    current_user.hashed_password = hash_password(request.new_password)
    current_user.must_change_password = False
    db.commit()
    return {"message": "Password changed successfully."}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_admin)):
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "role": current_user.role,
    }
