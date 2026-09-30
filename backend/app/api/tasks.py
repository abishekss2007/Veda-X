from datetime import date, datetime, timezone
from typing import Any, Literal, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.audit import log_audit_event
from ..db.database import get_db
from ..db.models import User
from .deps import get_current_user, require_role

router = APIRouter(prefix="/tasks", tags=["Tasks"])

TASK_ROLES = [
    "Principal Investigator",
    "Research Coordinator",
    "Doctor / Investigator",
    "Monitor",
    "EC Member",
    "PV Officer",
    "Admin",
    "Auditor / Regulator",
    "Institution Leadership",
]
TASK_PRIORITIES = ("Normal", "High", "Critical")
TASK_STATUSES = ("Assigned", "In progress", "Done")
_tasks: list[dict[str, Any]] = []


class TaskCreateIn(BaseModel):
    assignee: str = Field(..., min_length=1, max_length=320)
    title: str = Field(..., min_length=1, max_length=160)
    description: str = Field(..., max_length=4000)
    study_id: str = Field(..., min_length=1, max_length=100)
    site_id: str = Field(..., min_length=1, max_length=50)
    priority: Literal["Normal", "High", "Critical"]
    due_date: date


class TaskPatchIn(BaseModel):
    status: Optional[Literal["Assigned", "In progress", "Done"]] = None
    assignee: Optional[str] = Field(None, min_length=1, max_length=320)
    title: Optional[str] = Field(None, min_length=1, max_length=160)
    description: Optional[str] = Field(None, max_length=4000)
    study_id: Optional[str] = Field(None, min_length=1, max_length=100)
    site_id: Optional[str] = Field(None, min_length=1, max_length=50)
    priority: Optional[Literal["Normal", "High", "Critical"]] = None
    due_date: Optional[date] = None


def _resolve_assignee(assignee: str, db: Session) -> dict[str, Optional[str]]:
    if assignee.startswith("role:"):
        role = assignee.removeprefix("role:")
        if role not in TASK_ROLES:
            raise HTTPException(status_code=422, detail="Choose an approved role or active user.")
        return {"assignee": role, "assignee_email": None, "assignee_role": role}

    if assignee.startswith("user:"):
        email = assignee.removeprefix("user:").strip().lower()
        user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()
        if not user:
            raise HTTPException(status_code=422, detail="Assignee must be an active approved user.")
        return {
            "assignee": f"{user.full_name} ({user.role})",
            "assignee_email": user.email.lower(),
            "assignee_role": user.role,
        }

    raise HTTPException(status_code=422, detail="Choose an approved role or active user.")


def _with_overdue(task: dict[str, Any]) -> dict[str, Any]:
    result = dict(task)
    due_date = date.fromisoformat(result["due_date"])
    days_overdue = (date.today() - due_date).days
    result["overdue"] = days_overdue > 0 and result["status"] != "Done"
    result["overdue_reason"] = (
        f"Due date passed {days_overdue} day(s) ago; status is {result['status']}."
        if result["overdue"] else None
    )
    return result


@router.get("/assignees")
def list_assignees(
    current_user: User = Depends(require_role(["Admin", "Research Coordinator"])),
    db: Session = Depends(get_db),
):
    users = db.query(User).filter(User.is_active.is_(True)).order_by(User.full_name).all()
    roles = TASK_ROLES
    if current_user.role == "Research Coordinator":
        roles = [role for role in TASK_ROLES if role not in {"Admin", "Principal Investigator"}]
        users = [user for user in users if user.role not in {"Admin", "Principal Investigator"}]
    return {
        "roles": roles,
        "users": [
            {"email": user.email, "full_name": user.full_name, "role": user.role, "site_id": user.site_id}
            for user in users
        ],
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_task(
    req: TaskCreateIn,
    request: Request,
    current_user: User = Depends(require_role(["Admin", "Research Coordinator"])),
    db: Session = Depends(get_db),
):
    assignee = _resolve_assignee(req.assignee, db)
    if current_user.role == "Research Coordinator" and assignee["assignee_role"] in {"Admin", "Principal Investigator"}:
        raise HTTPException(status_code=403, detail="Research Coordinators cannot assign tasks to Admin or Principal Investigator.")
    task = {
        "id": str(uuid4()),
        **assignee,
        "title": req.title.strip(),
        "description": req.description.strip(),
        "study_id": req.study_id.strip(),
        "site_id": req.site_id.strip(),
        "priority": req.priority,
        "due_date": req.due_date.isoformat(),
        "status": "Assigned",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user.email,
        "created_by_role": current_user.role,
    }
    _tasks.insert(0, task)
    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        role=current_user.role,
        ip_address=request.client.host if request.client else "127.0.0.1",
        action="TASK_ASSIGNED",
        entity_type="Task",
        entity_id=task["id"],
        details=f"Assigned '{task['title']}' to {task['assignee']}; due {task['due_date']}.",
        site_id=current_user.site_id,
    )
    return _with_overdue(task)


@router.get("/assigned-by-me")
def list_tasks_assigned_by_me(current_user: User = Depends(require_role(["Research Coordinator"]))):
    return [
        _with_overdue(task)
        for task in _tasks
        if task["created_by"].lower() == current_user.email.lower()
    ]


@router.get("")
def list_tasks(current_user: User = Depends(get_current_user)):
    if current_user.role == "Admin":
        visible = _tasks
    else:
        visible = [
            task for task in _tasks
            if (task["assignee_email"] == current_user.email.lower()
                if task["assignee_email"] else task["assignee_role"] == current_user.role)
        ]
    return [_with_overdue(task) for task in visible]


@router.patch("/{task_id}")
def update_task(
    task_id: str,
    req: TaskPatchIn,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = next((item for item in _tasks if item["id"] == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")

    is_admin = current_user.role == "Admin"
    is_assignee = (
        task["assignee_email"] == current_user.email.lower()
        if task["assignee_email"] else task["assignee_role"] == current_user.role
    )
    if not is_admin and not is_assignee:
        raise HTTPException(status_code=403, detail="Only the assignee or Admin can update this task.")

    changes = req.model_dump(exclude_unset=True)
    if not is_admin and (set(changes) - {"status"} or changes.get("status") not in {"In progress", "Done"}):
        raise HTTPException(status_code=403, detail="Assignees may only set a task to In progress or Done.")

    old_status = task["status"]
    if "assignee" in changes:
        task.update(_resolve_assignee(changes.pop("assignee"), db))
    for field, value in changes.items():
        if field == "due_date" and value is not None:
            value = value.isoformat()
        if value is not None:
            task[field] = value

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        role=current_user.role,
        ip_address=request.client.host if request.client else "127.0.0.1",
        action="TASK_UPDATED",
        entity_type="Task",
        entity_id=task["id"],
        previous_value=old_status,
        new_value=task["status"],
        details=f"Task '{task['title']}' updated by {current_user.email}.",
        site_id=current_user.site_id,
    )
    return _with_overdue(task)