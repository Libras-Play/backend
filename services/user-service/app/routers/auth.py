"""
Authentication endpoints for User Service

Handles signup, login, token refresh using AWS Cognito
"""
import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
import logging
from typing import Optional

from app.config import get_settings
from app.dynamo import create_user

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Initialize Cognito client
cognito_client = boto3.client('cognito-idp', region_name=settings.AWS_REGION)


# ============= SCHEMAS =============

class SignUpRequest(BaseModel):
    """Sign up request schema"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (min 8 chars, uppercase, lowercase, number, symbol)")
    username: str = Field(..., min_length=3, max_length=50, description="Display username")
    preferredLanguage: Optional[str] = Field(default="pt-BR", description="UI language")
    preferredSignLanguage: Optional[str] = Field(default="LSB", description="Sign language to learn")


class SignUpResponse(BaseModel):
    """Sign up response schema"""
    message: str
    userId: str  # Cognito sub
    email: str
    username: str
    confirmationRequired: bool


class LoginRequest(BaseModel):
    """Login request schema"""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response schema"""
    accessToken: str
    idToken: str
    refreshToken: str
    expiresIn: int  # seconds
    tokenType: str = "Bearer"
    userId: str  # Cognito sub
    email: str
    username: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema"""
    refreshToken: str


class RefreshTokenResponse(BaseModel):
    """Refresh token response schema"""
    accessToken: str
    idToken: str
    expiresIn: int
    tokenType: str = "Bearer"


class ConfirmSignUpRequest(BaseModel):
    """Confirm sign up request schema"""
    email: EmailStr
    confirmationCode: str


class ForgotPasswordRequest(BaseModel):
    """Forgot password request schema"""
    email: EmailStr


class ConfirmForgotPasswordRequest(BaseModel):
    """Confirm forgot password request schema"""
    email: EmailStr
    confirmationCode: str
    newPassword: str = Field(..., min_length=8)


# ============= ENDPOINTS =============

@router.post("/signup", response_model=SignUpResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignUpRequest):
    """
    Register a new user in Cognito and create profile in DynamoDB
    
    **Flow:**
    1. Create user in Cognito with email/password
    2. Cognito sends verification email
    3. Create user profile in DynamoDB with Cognito sub as userId
    
    **Password Requirements:**
    - Minimum 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 number
    - At least 1 special character
    
    **Returns:**
    - User ID (Cognito sub)
    - Confirmation required (true if email verification needed)
    """
    try:
        # Sign up user in Cognito
        response = cognito_client.sign_up(
            ClientId=settings.COGNITO_CLIENT_ID,
            Username=payload.email,  # Use email as username
            Password=payload.password,
            UserAttributes=[
                {'Name': 'email', 'Value': payload.email},
                {'Name': 'name', 'Value': payload.username},
                {'Name': 'preferred_username', 'Value': payload.username},
            ]
        )
        
        cognito_sub = response['UserSub']
        
        logger.info(f"Created Cognito user: {cognito_sub} ({payload.email})")
        
        # Create user profile in DynamoDB
        user_profile = await create_user({
            'userId': cognito_sub,  # Use Cognito sub as userId
            'email': payload.email,
            'username': payload.username,
            'preferredLanguage': payload.preferredLanguage,
            'preferredSignLanguage': payload.preferredSignLanguage,
        })
        
        logger.info(f"Created user profile in DynamoDB: {cognito_sub}")
        
        return SignUpResponse(
            message="User registered successfully. Please check your email for verification code.",
            userId=cognito_sub,
            email=payload.email,
            username=payload.username,
            confirmationRequired=not response.get('UserConfirmed', False)
        )
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        logger.error(f"Cognito error during signup: {error_code} - {error_message}")
        
        if error_code == 'UsernameExistsException':
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists"
            )
        elif error_code == 'InvalidPasswordException':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password does not meet requirements (8+ chars, uppercase, lowercase, number, symbol)"
            )
        elif error_code == 'InvalidParameterException':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Registration failed: {error_message}"
            )
    except Exception as e:
        logger.error(f"Error during signup: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    """
    Authenticate user and get JWT tokens
    
    **Flow:**
    1. Authenticate with Cognito using email/password
    2. Receive access token, ID token, and refresh token
    
    **Tokens:**
    - **Access Token**: Use for API authorization (expires in 1 hour)
    - **ID Token**: Contains user claims (expires in 1 hour)
    - **Refresh Token**: Use to get new tokens (expires in 30 days)
    
    **Usage:**
    ```
    Authorization: Bearer <accessToken>
    ```
    """
    try:
        response = cognito_client.initiate_auth(
            ClientId=settings.COGNITO_CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': payload.email,
                'PASSWORD': payload.password,
            }
        )
        
        auth_result = response['AuthenticationResult']
        
        # Decode ID token to get user info
        import jwt
        id_token_payload = jwt.decode(
            auth_result['IdToken'],
            options={"verify_signature": False}  # Already verified by Cognito
        )
        
        logger.info(f"User logged in: {id_token_payload.get('sub')} ({payload.email})")
        
        return LoginResponse(
            accessToken=auth_result['AccessToken'],
            idToken=auth_result['IdToken'],
            refreshToken=auth_result['RefreshToken'],
            expiresIn=auth_result['ExpiresIn'],
            tokenType='Bearer',
            userId=id_token_payload.get('sub'),
            email=id_token_payload.get('email'),
            username=id_token_payload.get('cognito:username', id_token_payload.get('email'))
        )
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        logger.warning(f"Login failed for {payload.email}: {error_code}")
        
        if error_code == 'NotAuthorizedException':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        elif error_code == 'UserNotConfirmedException':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email not verified. Please check your email for verification code."
            )
        elif error_code == 'UserNotFoundException':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Login failed: {error_message}"
            )
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(payload: RefreshTokenRequest):
    """
    Refresh access and ID tokens using refresh token
    
    **When to use:**
    - Access token expired (after 1 hour)
    - Before making API calls if token might expire soon
    
    **Returns:**
    - New access token
    - New ID token
    - Refresh token (same as provided)
    """
    try:
        response = cognito_client.initiate_auth(
            ClientId=settings.COGNITO_CLIENT_ID,
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters={
                'REFRESH_TOKEN': payload.refreshToken,
            }
        )
        
        auth_result = response['AuthenticationResult']
        
        return RefreshTokenResponse(
            accessToken=auth_result['AccessToken'],
            idToken=auth_result['IdToken'],
            expiresIn=auth_result['ExpiresIn'],
            tokenType='Bearer'
        )
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.warning(f"Token refresh failed: {error_code}")
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    except Exception as e:
        logger.error(f"Error during token refresh: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/confirm-signup")
async def confirm_signup(payload: ConfirmSignUpRequest):
    """
    Confirm email with verification code sent during signup
    
    **Flow:**
    1. User receives verification code via email
    2. User submits email + code
    3. Cognito confirms account
    4. User can now login
    """
    try:
        cognito_client.confirm_sign_up(
            ClientId=settings.COGNITO_CLIENT_ID,
            Username=payload.email,
            ConfirmationCode=payload.confirmationCode
        )
        
        logger.info(f"Email confirmed for user: {payload.email}")
        
        return {"message": "Email verified successfully. You can now login."}
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        logger.warning(f"Email confirmation failed for {payload.email}: {error_code}")
        
        if error_code == 'CodeMismatchException':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code"
            )
        elif error_code == 'ExpiredCodeException':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification code has expired. Please request a new one."
            )
        elif error_code == 'NotAuthorizedException':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already confirmed"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Confirmation failed: {error_message}"
            )


@router.post("/resend-confirmation")
async def resend_confirmation(email: EmailStr):
    """
    Resend verification code to email
    
    **Use when:**
    - User didn't receive verification email
    - Verification code expired
    """
    try:
        cognito_client.resend_confirmation_code(
            ClientId=settings.COGNITO_CLIENT_ID,
            Username=email
        )
        
        logger.info(f"Resent confirmation code to: {email}")
        
        return {"message": "Verification code sent to your email"}
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.warning(f"Resend confirmation failed for {email}: {error_code}")
        
        if error_code == 'UserNotFoundException':
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        elif error_code == 'InvalidParameterException':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already confirmed"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to resend confirmation code"
            )


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest):
    """
    Initiate password reset flow
    
    **Flow:**
    1. User requests password reset
    2. Cognito sends reset code to email
    3. User submits code + new password to /confirm-forgot-password
    """
    try:
        cognito_client.forgot_password(
            ClientId=settings.COGNITO_CLIENT_ID,
            Username=payload.email
        )
        
        logger.info(f"Password reset initiated for: {payload.email}")
        
        return {"message": "Password reset code sent to your email"}
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.warning(f"Forgot password failed for {payload.email}: {error_code}")
        
        if error_code == 'UserNotFoundException':
            # Don't reveal if user exists
            return {"message": "If the email exists, a reset code will be sent"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initiate password reset"
            )


@router.post("/confirm-forgot-password")
async def confirm_forgot_password(payload: ConfirmForgotPasswordRequest):
    """
    Complete password reset with confirmation code
    
    **Flow:**
    1. User received code from /forgot-password
    2. User submits email + code + new password
    3. Cognito updates password
    4. User can login with new password
    """
    try:
        cognito_client.confirm_forgot_password(
            ClientId=settings.COGNITO_CLIENT_ID,
            Username=payload.email,
            ConfirmationCode=payload.confirmationCode,
            Password=payload.newPassword
        )
        
        logger.info(f"Password reset completed for: {payload.email}")
        
        return {"message": "Password reset successfully. You can now login with your new password."}
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        logger.warning(f"Confirm forgot password failed for {payload.email}: {error_code}")
        
        if error_code == 'CodeMismatchException':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid confirmation code"
            )
        elif error_code == 'ExpiredCodeException':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Confirmation code has expired. Please request a new one."
            )
        elif error_code == 'InvalidPasswordException':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password does not meet requirements"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Password reset failed: {error_message}"
            )
