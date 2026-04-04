from fastapi import APIRouter, HTTPException, status, Depends

from models import UserCreate, UserLogin, Token, UserOut
from auth import hash_password, verify_password, create_access_token, get_current_user, TokenData
from database import get_db

router = APIRouter(prefix="/auth", tags=["Auth"])


# ─── Signup ────────────────────────────────────────────────────────────────────

@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
async def signup(body: UserCreate):
    db = get_db()

    # Check if email already exists
    existing = db.table("users").select("id").eq("email", body.email).execute()
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    hashed = hash_password(body.password)

    result = db.table("users").insert({
        "name": body.name,
        "email": body.email,
        "hashed_password": hashed,
    }).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user. Please try again.",
        )

    user_row = result.data[0]
    token = create_access_token(user_id=user_row["id"], email=user_row["email"])

    return Token(
        access_token=token,
        user=UserOut(
            id=user_row["id"],
            name=user_row["name"],
            email=user_row["email"],
            created_at=str(user_row.get("created_at", "")),
        ),
    )


# ─── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=Token)
async def login(body: UserLogin):
    db = get_db()

    result = db.table("users").select("*").eq("email", body.email).execute()
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    user_row = result.data[0]

    if not verify_password(body.password, user_row["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_access_token(user_id=user_row["id"], email=user_row["email"])

    return Token(
        access_token=token,
        user=UserOut(
            id=user_row["id"],
            name=user_row["name"],
            email=user_row["email"],
            created_at=str(user_row.get("created_at", "")),
        ),
    )


# ─── Me (protected) ────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserOut)
async def me(token_data: TokenData = Depends(get_current_user)):
    db = get_db()

    result = db.table("users").select("id, name, email, created_at").eq("id", token_data.user_id).execute()
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    user_row = result.data[0]
    return UserOut(
        id=user_row["id"],
        name=user_row["name"],
        email=user_row["email"],
        created_at=str(user_row.get("created_at", "")),
    )
