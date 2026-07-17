from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.router import api_router
from app.db.dependencies import get_db_session
from app.modules.auth.dependencies import get_current_user_record
from app.modules.jobs.dependencies import get_job_service, get_repository_index_task
from app.modules.jobs.enums import JobStatus, JobType
from app.modules.jobs.schemas import JobRead
from app.modules.jobs.service import JobRepositoryNotFoundError


OWNER_ID = UUID("00000000-0000-0000-0000-000000000001")
REPOSITORY_ID = UUID("00000000-0000-0000-0000-000000000002")
JOB_ID = UUID("00000000-0000-0000-0000-000000000003")


def make_job_read(status: JobStatus = JobStatus.QUEUED) -> JobRead:
    timestamp = datetime.now(UTC)
    return JobRead(
        id=JOB_ID,
        repository_id=REPOSITORY_ID,
        job_type=JobType.REPOSITORY_INDEX,
        status=status,
        celery_task_id=None,
        error_message=None,
        started_at=None,
        completed_at=None,
        created_at=timestamp,
        updated_at=timestamp,
    )


class FakeJobService:
    def __init__(self, *, created: bool = True, error: Exception | None = None) -> None:
        self.created = created
        self.error = error
        self.attached_task_id: str | None = None
        self.failed_message: str | None = None

    async def get_job(self, session, job_id, owner_id):
        del session, job_id, owner_id
        if self.error:
            raise self.error
        return make_job_read(JobStatus.RUNNING)

    async def create_repository_index_job(self, session, repository_id, owner_id):
        del session, repository_id, owner_id
        if self.error:
            raise self.error
        status = JobStatus.QUEUED if self.created else JobStatus.RUNNING
        return make_job_read(status), self.created

    async def attach_celery_task(self, session, job_id, celery_task_id):
        del session, job_id
        self.attached_task_id = celery_task_id
        job = make_job_read(JobStatus.QUEUED)
        job.celery_task_id = celery_task_id
        return job

    async def mark_failed(self, session, job_id, error_message):
        del session, job_id
        self.failed_message = error_message
        return make_job_read(JobStatus.FAILED)


class FakeIndexTask:
    def __init__(self) -> None:
        self.delay_args: tuple[str, str] | None = None

    def delay(self, job_id: str, repository_id: str):
        self.delay_args = (job_id, repository_id)
        return SimpleNamespace(id="celery-task-id")


def make_app(
    job_service: FakeJobService,
    index_task: FakeIndexTask | None = None,
) -> FastAPI:
    app = FastAPI()
    app.include_router(api_router)
    user = SimpleNamespace(id=OWNER_ID)

    async def fake_session():
        yield object()

    app.dependency_overrides[get_current_user_record] = lambda: user
    app.dependency_overrides[get_job_service] = lambda: job_service
    app.dependency_overrides[get_repository_index_task] = lambda: index_task or FakeIndexTask()
    app.dependency_overrides[get_db_session] = fake_session
    return app


def test_repository_index_creates_job_and_enqueues_task() -> None:
    job_service = FakeJobService(created=True)
    index_task = FakeIndexTask()
    app = make_app(job_service, index_task)

    with TestClient(app) as client:
        response = client.post(f"/api/v1/repositories/{REPOSITORY_ID}/index")

    assert response.status_code == 202
    assert response.json() == {
        "repository_id": str(REPOSITORY_ID),
        "job_id": str(JOB_ID),
        "status": "queued",
    }
    assert index_task.delay_args == (str(JOB_ID), str(REPOSITORY_ID))
    assert job_service.attached_task_id == "celery-task-id"


def test_repository_index_returns_existing_active_job_without_enqueueing() -> None:
    job_service = FakeJobService(created=False)
    index_task = FakeIndexTask()
    app = make_app(job_service, index_task)

    with TestClient(app) as client:
        response = client.post(f"/api/v1/repositories/{REPOSITORY_ID}/index")

    assert response.status_code == 202
    assert response.json()["status"] == "running"
    assert index_task.delay_args is None


def test_repository_index_repository_not_found_is_404() -> None:
    app = make_app(FakeJobService(error=JobRepositoryNotFoundError()))

    with TestClient(app) as client:
        response = client.post(f"/api/v1/repositories/{REPOSITORY_ID}/index")

    assert response.status_code == 404


def test_repository_index_requires_authentication() -> None:
    app = FastAPI()
    app.include_router(api_router)

    with TestClient(app) as client:
        response = client.post(f"/api/v1/repositories/{REPOSITORY_ID}/index")

    assert response.status_code == 401


def test_job_status_returns_owner_scoped_job() -> None:
    app = make_app(FakeJobService())

    with TestClient(app) as client:
        response = client.get(f"/api/v1/jobs/{JOB_ID}")

    assert response.status_code == 200
    assert response.json()["id"] == str(JOB_ID)
    assert response.json()["status"] == "running"
