"""In-memory session store: one entry per uploaded file.

The app runs locally for a single user (the demo), so a dict is enough; the
data is lost when the server restarts.
"""

import uuid
from dataclasses import dataclass, field

import pandas as pd
from fastapi import HTTPException

from app.findings import Finding
from app.i18n import t
from app.split import SplitResult
from app.transforms import ApplyResult


@dataclass
class Session:
    raw: pd.DataFrame
    filename: str
    sheet: str | None
    sheets: list[str]
    types: dict                      # effective types (inferred + user overrides)
    inferred_types: dict = field(default_factory=dict)
    repairs: dict = field(default_factory=dict)   # {column: cells repaired at upload} (Excel-swapped dates)
    mode: str | None = None
    target: str | None = None
    split: SplitResult | None = None
    findings: list[Finding] = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    result: ApplyResult | None = None
    choices: dict = field(default_factory=dict)


SESSIONS: dict[str, Session] = {}


def create(session: Session) -> str:
    sid = uuid.uuid4().hex
    SESSIONS[sid] = session
    return sid


def get(sid: str) -> Session:
    try:
        return SESSIONS[sid]
    except KeyError:
        raise HTTPException(status_code=404, detail=t("error.unknown_session")) from None
