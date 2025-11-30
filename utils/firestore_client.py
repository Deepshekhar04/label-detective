"""
Database client for Label Detective using Google Firestore.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from utils.logging_utils import get_logger
from google.cloud import firestore

logger = get_logger("database")

# Global database connection
_db_connection = None


def initialize_db():
    """Initialize Firestore database connection."""
    global _db_connection

    try:
        project_id = os.getenv("FIRESTORE_PROJECT_ID")
        database_id = os.getenv("FIRESTORE_DATABASE_ID", "firestoredb")
        _db_connection = firestore.Client(project=project_id, database=database_id)
        logger.info(f"Initialized Firestore client with database: {database_id}")
    except Exception as e:
        logger.error(f"Failed to initialize Firestore: {e}")
        raise


def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve user profile from Firestore."""
    doc_ref = _db_connection.collection("users").document(user_id)
    doc = doc_ref.get()
    return doc.to_dict() if doc.exists else None


def save_user(user_id: str, profile_data: Dict[str, Any]) -> None:
    """Save or update user profile."""
    profile_data["last_active_at"] = datetime.utcnow().isoformat()
    doc_ref = _db_connection.collection("users").document(user_id)
    doc_ref.set(profile_data, merge=True)
    logger.info(f"Saved user profile for {user_id}")


def save_session(session_data: Dict[str, Any]) -> None:
    """Save session trace with automatic TTL management."""
    session_id = session_data["session_id"]
    ttl_days = int(os.getenv("SESSION_TTL_DAYS", "30"))
    ttl_date = (datetime.utcnow() + timedelta(days=ttl_days)).isoformat()

    session_data["ttl_date"] = ttl_date
    doc_ref = _db_connection.collection("sessions").document(session_id)
    doc_ref.set(session_data)
    logger.info(f"Saved session {session_id}")


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve session by ID."""
    doc_ref = _db_connection.collection("sessions").document(session_id)
    doc = doc_ref.get()
    return doc.to_dict() if doc.exists else None


def save_scan_history(user_id: str, scan_summary: Dict[str, Any]) -> str:
    """Save scan to user's history."""
    from utils.logging_utils import create_trace_id

    scan_id = create_trace_id()

    doc_ref = (
        _db_connection.collection("history")
        .document(user_id)
        .collection("scans")
        .document(scan_id)
    )
    doc_ref.set(scan_summary)
    logger.info(f"Saved scan history for user {user_id}")
    return scan_id


def get_scan_history(
    user_id: str, filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Retrieve user's scan history with optional filters.

    Args:
        user_id: User identifier
        filters: Optional filters (verdict, date_from, date_to)

    Returns:
        List of scan summaries
    """
    query = _db_connection.collection("history").document(user_id).collection("scans")

    if filters:
        if "verdict" in filters:
            query = query.where("verdict", "==", filters["verdict"])

    docs = query.stream()
    return [doc.to_dict() for doc in docs]


def create_pending_review(user_id: str, session_id: str, reason: str) -> str:
    """
    Create a pending review for human-in-the-loop confirmation.

    Args:
        user_id: User identifier
        session_id: Session requiring review
        reason: Reason for requiring review

    Returns:
        review_id
    """
    from utils.logging_utils import create_trace_id

    review_id = create_trace_id()

    review_data = {
        "review_id": review_id,
        "session_id": session_id,
        "user_id": user_id,
        "status": "pending",
        "reason": reason,
        "notes": "",
        "assigned_to": "",
        "created_at": datetime.utcnow().isoformat(),
    }

    doc_ref = _db_connection.collection("reviews").document(review_id)
    doc_ref.set(review_data)
    logger.info(f"Created pending review {review_id}")
    return review_id


def get_pending_reviews(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get pending reviews, optionally filtered by user."""
    query = _db_connection.collection("reviews").where("status", "==", "pending")
    if user_id:
        query = query.where("user_id", "==", user_id)
    docs = query.stream()
    return [doc.to_dict() for doc in docs]


def update_review_status(review_id: str, status: str, notes: str = "") -> None:
    """Update review status."""
    doc_ref = _db_connection.collection("reviews").document(review_id)
    doc_ref.update({"status": status, "notes": notes})
    logger.info(f"Updated review {review_id} to status {status}")


def save_memory(user_id: str, fact: Dict[str, Any]) -> None:
    """
    Store long-term memory fact for persistent storage.

    Args:
        user_id: User identifier
        fact: Memory fact dictionary
    """
    from utils.logging_utils import create_trace_id

    fact_id = create_trace_id()
    fact["fact_id"] = fact_id
    fact["created_at"] = datetime.utcnow().isoformat()

    doc_ref = (
        _db_connection.collection("memories")
        .document(user_id)
        .collection("facts")
        .document(fact_id)
    )
    doc_ref.set(fact)
    logger.info(f"Saved memory fact for user {user_id}")


def fetch_memories(
    user_id: str, filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Query long-term memory facts.

    Args:
        user_id: User identifier
        filters: Optional filters (type, subject)

    Returns:
        List of memory facts
    """
    query = _db_connection.collection("memories").document(user_id).collection("facts")

    if filters:
        if "type" in filters:
            query = query.where("type", "==", filters["type"])
        if "subject" in filters:
            query = query.where("subject", "==", filters["subject"])

    docs = query.stream()
    return [doc.to_dict() for doc in docs]
