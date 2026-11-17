"""Review rating service.
Encapsulates review rating business logic."""

from config import (
    REVIEW_RATING_TABLE_NAME,
    REVIEW_RATING_COL_SIGNUP_ID, REVIEW_RATING_COL_ACTIVITY_ID,
    REVIEW_RATING_COL_REVIEWER_NAME, REVIEW_RATING_COL_RATER_NAME,
    REVIEW_RATING_COL_SCORE, REVIEW_RATING_COL_WEIGHT, REVIEW_RATING_COL_COMMENT,
    TABLE_ROWS_CACHE_TTL_SECONDS
)
from models import db
from utils import ValidationError, NotFoundError
from utils.versioned_cache import cached_build, touch_version


def list_review_ratings():
    """List all review ratings using the versioned cache."""
    return cached_build(
        'review_ratings',
        TABLE_ROWS_CACHE_TTL_SECONDS,
        lambda: db.list_rows(REVIEW_RATING_TABLE_NAME) or [],
    )


def get_rating_by_id(rating_id):
    """Get a rating by ID."""
    if not rating_id:
        return None
    ratings = list_review_ratings()
    for rating in ratings:
        if str(rating.get('_id')) == rating_id:
            return rating
    return None


def get_ratings_by_signup(signup_id):
    """List ratings for a signup."""
    ratings = list_review_ratings()
    return [r for r in ratings if str(r.get(REVIEW_RATING_COL_SIGNUP_ID, '')).strip() == signup_id]


def serialize_rating(rating):
    """Serialize a review rating."""
    if not rating:
        return None
    return {
        'id': str(rating.get('_id', '')),
        'signup_id': str(rating.get(REVIEW_RATING_COL_SIGNUP_ID, '')).strip(),
        'activity_id': str(rating.get(REVIEW_RATING_COL_ACTIVITY_ID, '')).strip(),
        'reviewer_name': str(rating.get(REVIEW_RATING_COL_REVIEWER_NAME, '')).strip(),
        'rater_name': str(rating.get(REVIEW_RATING_COL_RATER_NAME, '')).strip(),
        'score': float(rating.get(REVIEW_RATING_COL_SCORE, 0) or 0),
        'weight': float(rating.get(REVIEW_RATING_COL_WEIGHT, 0) or 0),
        'comment': str(rating.get(REVIEW_RATING_COL_COMMENT, '')).strip(),
    }


def create_review_rating(signup_id, activity_id, reviewer_name, rater_name, score, weight=1.0, comment=''):
    """Create a review rating."""
    if not signup_id or not activity_id or not reviewer_name or not rater_name:
        raise ValidationError("Complete all rating fields")

    if score < 0 or score > 10:
        raise ValidationError("The score must be between 0 and 10")

    from datetime import datetime
    row_data = {
        REVIEW_RATING_COL_SIGNUP_ID: signup_id,
        REVIEW_RATING_COL_ACTIVITY_ID: activity_id,
        REVIEW_RATING_COL_REVIEWER_NAME: reviewer_name,
        REVIEW_RATING_COL_RATER_NAME: rater_name,
        REVIEW_RATING_COL_SCORE: score,
        REVIEW_RATING_COL_WEIGHT: weight,
        REVIEW_RATING_COL_COMMENT: comment,
    }

    result = db.append_row(REVIEW_RATING_TABLE_NAME, row_data)
    touch_version()
    return serialize_rating(result)