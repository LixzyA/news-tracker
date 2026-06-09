import resend
import os
from fastapi import HTTPException
from dotenv import load_dotenv
load_dotenv()

RESEND_API_KEY = os.getenv("RESEND_API_FULL", "")
resend.api_key = RESEND_API_KEY

def add_contact(email: str) -> str:
    params: resend.Contacts.CreateParams = {
        "email": email,
        "unsubscribed": False,
    }
    try:
        response = resend.Contacts.create(params)
        return response["id"]
    except Exception as e:
        raise HTTPException(status_code = 500, detail=str(e))

def update_contact(email: str, unsubscribed: bool) -> str:
    params: resend.Contacts.UpdateParams = {
        "email": email,
        "unsubscribed": unsubscribed,
    }
    try:
        response = resend.Contacts.update(params)
        return response["id"]
    except Exception as e:
        raise HTTPException(status_code = 500, detail=str(e))


def add_contact_to_segment(*, email: str| None = None, contact_id: str| None = None) -> str:
    """
    Accepts either an email or a contact_id to add to specified Resend segment. Returns the segment_contact_id on success.
    """
    resend_segment_id: str = os.getenv("RESEND_SEGMENT_ID", "67721360-47af-4f4a-a227-5cdc143e0195")
    if not email and not contact_id:
        raise HTTPException(status_code = 400, detail="Either email or contact_id must be provided.")
    elif isinstance(email, str):
        params: resend.ContactSegments.AddParams = {
            "segment_id": resend_segment_id,
            "email": email,
        }
    elif isinstance(contact_id, str):
        params: resend.ContactSegments.AddParams = {
            "segment_id": resend_segment_id,
            "contact_id": contact_id,
        }
        
    try:
        response = resend.Contacts.Segments.add(params)
        return response["id"]
    except Exception as e:
        raise HTTPException(status_code = 500, detail=str(e))
    
def remove_contact_from_segment(*, email: str| None = None, contact_id: str| None = None) -> str:
    resend_segment_id: str = os.getenv("RESEND_SEGMENT_ID", "67721360-47af-4f4a-a227-5cdc143e0195")
    if not email and not contact_id:
        raise HTTPException(status_code = 400, detail="Either email or contact_id must be provided.")
    elif isinstance(email, str):
        params: resend.ContactSegments.AddParams = {
            "segment_id": resend_segment_id,
            "email": email,
        }
    elif isinstance(contact_id, str):
        params: resend.ContactSegments.AddParams = {
            "segment_id": resend_segment_id,
            "contact_id": contact_id,
        }
    try:
        response = resend.Contacts.Segments.remove(params)
        return response["id"]
    except Exception as e:
        raise HTTPException(status_code = 500, detail=str(e))

def broadcast_email(from_email: str, subject: str, html_content: str) -> str:
    '''
    Broadcasts an email to the specified segment. Returns the broadcast_id on success.
    '''
    params: resend.Broadcasts.CreateParams = {
        "segment_id": os.getenv("RESEND_SEGMENT_ID", "67721360-47af-4f4a-a227-5cdc143e0195"),
        "from": from_email,
        "subject": subject,
        "html": html_content,
    }
    try:
        response = resend.Broadcasts.create(params)
        return response["id"]
    except Exception as e:
        raise HTTPException(status_code = 500, detail=str(e))

def send_broadcast(broadcast_id: str) -> str:
    '''
    Sends a previously created broadcast. Returns the broadcast_id on success.
    '''
    params: resend.Broadcasts.SendParams = {
        "broadcast_id": broadcast_id,
        "scheduled_at": "in 1 minute"
    }
    try:
        response = resend.Broadcasts.send(params)
        return response["id"]
    except Exception as e:
        raise HTTPException(status_code = 500, detail=str(e))