from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Contact
from ..schemas import ContactCreate, ContactResponse

router = APIRouter(
    prefix="/identity", # Keeping it future-proof as 'identity' service
    tags=["identity"]
)

# Mock user ID for MVP since we don't have full auth layer active in this context
TEST_USER_ID = 1

@router.get("/contacts", response_model=List[ContactResponse])
def get_contacts(db: Session = Depends(get_db)):
    # In a real app, filtering by current_user.id
    return db.query(Contact).filter(Contact.user_id == TEST_USER_ID).all()

@router.post("/contacts", response_model=ContactResponse)
def create_contact(contact: ContactCreate, db: Session = Depends(get_db)):
    # Check if exists
    existing = db.query(Contact).filter(Contact.user_id == TEST_USER_ID, Contact.address == contact.address).first()
    if existing:
        raise HTTPException(status_code=400, detail="Contact with this address already exists")
    
    new_contact = Contact(
        name=contact.name,
        address=contact.address,
        network=contact.network,
        user_id=TEST_USER_ID
    )
    db.add(new_contact)
    db.commit()
    db.refresh(new_contact)
    return new_contact

@router.delete("/contacts/{contact_id}")
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id, Contact.user_id == TEST_USER_ID).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
        
    db.delete(contact)
    db.commit()
    return {"ok": True}
