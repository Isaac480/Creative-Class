# authentication for data export

import logging
import random
import secrets
from collections import Counter
from datetime import datetime, timedelta
from functools import lru_cache
from operator import itemgetter
from pathlib import Path
from typing import Annotated, List, Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi_utils.tasks import repeat_every
from sqlmodel import Field, Session, SQLModel, create_engine, select

import config
from database import engine
from models import (
    POSSIBLE_PARTICIPANT_STATUSES,
    Data,
    ExperimentConfiguration,
    Participant,
    ParticipantDataIn,
    ParticipantIn,
    ParticipantOut,
    ParticipantUpdate,
)


@lru_cache()
def get_settings():
    return config.Settings()


def get_session():
    with Session(engine) as session:
        yield session


# Set up settings
settings = get_settings()

experiment_configuration_dict = dict(
    debug_mode=settings.debug_mode,
    estimated_task_duration=settings.estimated_task_duration,
    compensation=settings.compensation,
    experiment_title=settings.experiment_title,
    experiment_name=settings.experiment_name,
    version_date=settings.version_date,
    open_tags=settings.open_tags,
    close_tags=settings.close_tags,
    logrocket_id=settings.logrocket_id,
    intertrial_interval=settings.intertrial_interval,
    stimulus_width=settings.stimulus_width,
    stimulus_height=settings.stimulus_height,
    slider_width=settings.slider_width,
    num_stimuli=settings.num_stimuli,
)

app_name = settings.app_name

allotted_time = settings.allotted_time
shuffle = bool(settings.shuffle)
condition = settings.condition
refresh_time = settings.refresh_time
environment_type = settings.environment_type
openapi_url = "/openapi.json" if environment_type != "production" else None
docs_url = "/docs" if environment_type != "production" else None
redoc_url = "/redoc" if environment_type != "production" else None

# Set up app
app = FastAPI(openapi_url=openapi_url, docs_url=docs_url, redoc_url=redoc_url)

app.mount("/exp", StaticFiles(directory="./frontend", html=True), name="frontend")

# Set up logging
LOGGING_CONFIG = Path(__file__).parent / "logging.conf"

logging.config.fileConfig(LOGGING_CONFIG, disable_existing_loggers=False)

logger = logging.getLogger(__name__)

security = HTTPBasic()


def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(
        credentials.username, settings.admin_username
    )
    correct_password = secrets.compare_digest(
        credentials.password, settings.admin_password
    )
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# hide docs from user
@app.get("/docs", include_in_schema=False)
async def get_swagger_documentation(username: str = Depends(get_current_username)):
    return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")


@app.get("/redoc", include_in_schema=False)
async def get_redoc_documentation(username: str = Depends(get_current_username)):
    return get_redoc_html(openapi_url="/openapi.json", title="docs")


@app.get("/openapi.json", include_in_schema=False)
async def openapi(username: str = Depends(get_current_username)):
    return get_openapi(title=app.title, version=app.version, routes=app.routes)


@app.get("/")
async def redirect_to_exp(request: Request):
    query_params = request.query_params
    redirect_url = "/exp"

    if query_params:
        redirect_url += f"?{query_params}"

    return RedirectResponse(url=redirect_url)


@app.get("/ip")
def get_ip(request: Request):
    client_host = request.client.host
    return client_host


@app.post("/participants")
def create_participant(
    *, session: Session = Depends(get_session), participant: Participant
):
    session.add(participant)
    session.commit()
    session.refresh(participant)
    return participant


@app.patch("/participants", response_model=Participant)
def update_participant(
    *, session: Session = Depends(get_session), participant_update: ParticipantUpdate
):
    participant = session.exec(
        select(Participant).where(Participant.worker_id == participant_update.worker_id)
    ).first()

    if not participant.status:
        logger.error(
            f"Tried to update participant {participant.worker_id} which had no status"
        )

    if participant.status == "complete":
        logger.error(
            f"Tried to update participant {participant.worker_id} which was already complete"
        )
        return participant

    participant.status = participant_update.status

    if participant_update.end_time:
        participant.end_time = participant_update.end_time
    if participant_update.start_time:
        participant.start_time = participant_update.start_time
    if participant_update.data:
        participant.data = participant_update.data
        participant.data_id = participant_update.data_id

    session.add(participant)
    session.commit()
    session.refresh(participant)
    return participant


@app.post("/data")
def post_subject_data(
    *, session: Session = Depends(get_session), data: ParticipantDataIn
):
    # Create trial data
    print("here")
    print(f"data: {data.json_data}")
    trial_data = Data(condition=data.condition, json_data=data.json_data)
    session.add(trial_data)
    session.commit()
    session.refresh(trial_data)

    # update participant
    participant = session.exec(
        select(Participant).where(Participant.worker_id == data.worker_id)
    ).first()

    participant.worker_id = data.worker_id
    participant.status = "complete"
    participant.end_time = datetime.utcnow()
    participant.data = trial_data
    participant.data_id = trial_data.id

    session.add(participant)
    session.commit()
    session.refresh(participant)

    trial_data.participant = participant
    trial_data.worker_id = participant.worker_id

    session.add(trial_data)
    session.commit()
    session.refresh(trial_data)


@app.post("/KAI_data")
def post_KAI_data(
    *, session: Session = Depends(get_session), data: ParticipantDataIn
):
    """Store KAI survey responses separately from main experiment data."""
    if not data.KAI_responses:
        raise HTTPException(status_code=400, detail="No KAI responses provided")
    
    # Create KAI data entry
    kai_data = Data(
        condition=data.condition, 
        json_data=[{"KAI_responses": data.KAI_responses}]
    )
    session.add(kai_data)
    session.commit()
    session.refresh(kai_data)

    # Update participant status to indicate survey completion
    participant = session.exec(
        select(Participant).where(Participant.worker_id == data.worker_id)
    ).first()

    if participant.status == "started":
        participant.status = "working_finished_survey"
    elif participant.status.startswith("working"):
        participant.status = participant.status.replace("working", "working_finished_survey")

    session.add(participant)
    session.commit()
    session.refresh(participant)

    kai_data.participant = participant
    kai_data.worker_id = participant.worker_id

    session.add(kai_data)
    session.commit()
    session.refresh(kai_data)
    
    return {"message": "KAI survey data saved successfully", "data_id": kai_data.id}


@app.post("/KAI_survey_data")
def post_KAI_survey_data(
    *, session: Session = Depends(get_session), data: dict
):
    """Store KAI survey responses with flexible format."""
    worker_id = data.get("worker_id")
    condition = data.get("condition")
    KAI_responses = data.get("KAI_responses")
    
    if not worker_id or not condition or not KAI_responses:
        raise HTTPException(status_code=400, detail="Missing required fields: worker_id, condition, or KAI_responses")
    
    # Create KAI data entry
    kai_data = Data(
        condition=condition, 
        json_data=[{"KAI_responses": KAI_responses}]
    )
    session.add(kai_data)
    session.commit()
    session.refresh(kai_data)

    # Update participant status to indicate survey completion
    participant = session.exec(
        select(Participant).where(Participant.worker_id == worker_id)
    ).first()

    if participant.status == "started":
        participant.status = "working_finished_survey"
    elif participant.status.startswith("working"):
        participant.status = participant.status.replace("working", "working_finished_survey")

    session.add(participant)
    session.commit()
    session.refresh(participant)

    kai_data.participant = participant
    kai_data.worker_id = participant.worker_id

    session.add(kai_data)
    session.commit()
    session.refresh(kai_data)
    
    return {"message": "KAI survey data saved successfully", "data_id": kai_data.id}


@app.get("/participants")
async def read_participants(
    *,
    username: str = Depends(get_current_username),
    session: Session = Depends(get_session),
):
    participants = session.exec(select(Participant)).all()
    return participants


@app.get("/info")
def info(
    *,
    username: str = Depends(get_current_username),
    settings: config.Settings = Depends(get_settings),
):
    return {
        "app_name": settings.app_name,
        "allotted_time": settings.allotted_time,
    }


@app.get("/status")
def get_status(
    *,
    username: str = Depends(get_current_username),
    session: Session = Depends(get_session),
):
    """Log a summary of all the participants' status codes."""
    participants = session.exec(select(Participant)).all()
    counts = Counter([p.status for p in participants])
    sorted_counts = sorted(counts.items(), key=itemgetter(0))
    logger.info(f"Status summary: {str(sorted_counts)}")
    return sorted_counts


@app.post("/init", response_model=ExperimentConfiguration)
def initialize_experiment(
    *,
    session: Session = Depends(get_session),
    participant_in: ParticipantIn,
):
    """Initialize the experiment for a participant.
    Creates a participant.
    """

    # Check if participant already exists
    existing_participant = session.exec(
        select(Participant).where(Participant.worker_id == participant_in.worker_id)
    ).first()

    print("checked for existing participant")
    if existing_participant:
        # Update existing participant with current condition if it's different
        if existing_participant.condition != condition:
            logger.info(
                f"Participant {participant_in.worker_id} exists with condition '{existing_participant.condition}', updating to '{condition}'"
            )
            existing_participant.condition = condition
            session.add(existing_participant)
            session.commit()
            session.refresh(existing_participant)
        else:
            logger.info(
                f"Participant {participant_in.worker_id} already exists with correct condition '{condition}'."
            )
        
        experiment_configuration = ExperimentConfiguration(
            **experiment_configuration_dict,
            **existing_participant.dict(),
        )

        return experiment_configuration

    # Create new participant with current condition
    participant = Participant(
        worker_id=participant_in.worker_id,
        hit_id=participant_in.hit_id,
        assignment_id=participant_in.assignment_id,
        platform=participant_in.platform,
        condition=condition,
        status="started",
    )

    print("got to make participant")

    session.add(participant)
    session.commit()
    session.refresh(participant)

    experiment_configuration = ExperimentConfiguration(
        **experiment_configuration_dict,
        **participant.dict(),
    )
    return experiment_configuration


@app.on_event("startup")
@repeat_every(seconds=refresh_time)
@app.get("/refresh")
def update_incomplete_participants():
    with Session(engine) as session:
        # Find expired participants
        now = datetime.utcnow()
        min_start_time = now - timedelta(seconds=allotted_time)
        participants = session.exec(
            select(Participant)
            .where(Participant.end_time.is_(None))
            .where(Participant.status.in_(POSSIBLE_PARTICIPANT_STATUSES["working"]))
        ).all()
        updated_participants = []
        for participant in participants:
            if participant.start_time < min_start_time:
                participant.status = "timeout"
                session.add(participant)
                updated_participants.append(participant)
        session.commit()
        for p in updated_participants:
            session.refresh(p)
        logger.info(f"Updated participants: {updated_participants}")


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
