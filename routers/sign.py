import mimetypes
import uuid
from enum import Enum

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_
from starlette.responses import JSONResponse

from database import get_db
from models import User
from models.contract_invitation import ContractInvitation, InvitationStatus
from utils.auth import get_current_user
from utils.crypto import decrypt_private_key, sign_document, verify_signature, extract_signature
from models.keys import KeyPair
from models.signatures import Signature

router = APIRouter(dependencies=[Depends(get_current_user)])


class VerificationStatus(str, Enum):
    GREEN = "green"  # Valid + in contract relationship
    YELLOW = "yellow"  # Valid but not in contract relationship
    RED = "red"  # Invalid signature


@router.post("/signDownload")
async def sign_and_download(
        file: UploadFile = File(...),
        user_id: uuid.UUID = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Signs a document without requiring the user to provide their password manually."""

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalars().first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    key_result = await db.execute(select(KeyPair).where(KeyPair.user_id == user_id))
    key_pair = key_result.scalars().first()

    if not key_pair:
        raise HTTPException(status_code=404, detail="Key pair not found")

    try:
        file_content = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to read file")

    try:
        private_key_pem = decrypt_private_key(key_pair.private_key, user.hashed_password, user.encryption_salt)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Decryption failed: {str(e)}")

    signature = sign_document(file_content, private_key_pem.decode())

    signed_filename = f"signed_{file.filename}"
    signed_content = file_content + b"\n\n--- SIGNATURE START ---\n" + signature.encode() + b"\n--- SIGNATURE END ---"

    signed_entry = Signature(
        user_id=user_id,
        filename=signed_filename,
        signature=signature,
        content=signed_content
    )
    db.add(signed_entry)
    await db.commit()

    return JSONResponse(
        content={
            "filename": signed_filename,
            "signature": signature,
            "download_url": f"http://localhost:8000/sign/download/{signed_filename}"
        }
    )


@router.get("/download/{filename}")
async def download_file(filename: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Signature).where(Signature.filename == filename))
    signed_entry = result.scalars().first()
    if not signed_entry:
        raise HTTPException(status_code=404, detail="File not found")

    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type is None:
        mime_type = "application/octet-stream"

    return Response(
        content=signed_entry.content,
        media_type=mime_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/verify_signature")
async def verify_signed_file(
        file: UploadFile = File(...),
        user_id: uuid.UUID = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Verify a signed document.

    Returns:
    - GREEN: Valid signature + you have a contract relationship with signer
    - YELLOW: Valid signature but no contract relationship with signer
    - RED: Invalid or no signature
    """
    try:
        file_content = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to read file")

    original_content, signature = extract_signature(file_content)

    if not original_content or not signature:
        return JSONResponse(
            status_code=400,
            content={
                "status": VerificationStatus.RED,
                "message": "No signature found in the document",
                "verified": False
            }
        )

    # Find the signer by checking all public keys
    all_keys = await db.execute(select(KeyPair))
    key_pairs = all_keys.scalars().all()

    signer_id = None
    for key_pair in key_pairs:
        result = verify_signature(original_content, signature, key_pair.public_key)
        if result.get("verified"):
            signer_id = key_pair.user_id
            break

    if not signer_id:
        return JSONResponse(
            status_code=400,
            content={
                "status": VerificationStatus.RED,
                "message": "Invalid signature - no matching signer found",
                "verified": False
            }
        )

    # Get signer info
    signer_result = await db.execute(select(User).where(User.id == signer_id))
    signer = signer_result.scalars().first()
    signer_name = f"{signer.first_name} {signer.last_name}" if signer else "Unknown"

    # If verifier is the signer, green
    if signer_id == user_id:
        return JSONResponse(
            content={
                "status": VerificationStatus.GREEN,
                "message": "Signature is valid - this is your signature",
                "verified": True,
                "signer": signer_name
            }
        )

    # Check for accepted contract relationship between verifier and signer
    contract_result = await db.execute(
        select(ContractInvitation).where(
            ContractInvitation.status == InvitationStatus.ACCEPTED,
            or_(
                # Verifier sent invitation to signer
                (ContractInvitation.sender_id == user_id) & (ContractInvitation.receiver_id == signer_id),
                # Signer sent invitation to verifier
                (ContractInvitation.sender_id == signer_id) & (ContractInvitation.receiver_id == user_id)
            )
        )
    )
    has_relationship = contract_result.scalars().first() is not None

    if has_relationship:
        return JSONResponse(
            content={
                "status": VerificationStatus.GREEN,
                "message": "Signature is valid - signed by your contract partner",
                "verified": True,
                "signer": signer_name
            }
        )
    else:
        return JSONResponse(
            content={
                "status": VerificationStatus.YELLOW,
                "message": "Signature is valid but you have no contract relationship with the signer",
                "verified": True,
                "signer": signer_name
            }
        )