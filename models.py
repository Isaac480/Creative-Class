from datetime import datetime, timezone
from pydantic import root_validator
from sqlalchemy import Column
from sqlmodel import Field, Relationship, Session, SQLModel, select, JSON
from typing import Optional, List, Dict


POSSIBLE_PARTICIPANT_STATUSES = {
    "working": [
        "started",
        "working",
        "working_finished_consent",
        "working_finished_attrition",
        "working_finished_instructions",
        "working_finished_task",
        "working_finished_survey",
    ],
    "complete": ["complete"],
    "incomplete": ["timeout", "failed"],
}


class Participant(SQLModel, table=True):
    """The participant model.
    Possible statuses:
    - started
    - consented
    - in_instructions
    - working
    - complete
    - timeout
    - failed
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    worker_id: Optional[str] = Field(index=True)  # prolific_pid
    hit_id: Optional[str]  # study_id
    assignment_id: Optional[str]  # session_id
    platform: Optional[str]  # prolific or mturk or cloudresearch
    condition: Optional[str]
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    start_time: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    end_time: Optional[datetime]
    status: str = Field(default="started")
    data_id: Optional[int] = Field(default=None, foreign_key="data.id")
    data: Optional["Data"] = Relationship(back_populates="participant")

    class Config:
        arbitrary_types_allowed = True


class ParticipantUpdate(SQLModel):
    worker_id: str
    status: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    data: Optional["Data"]
    data_id: Optional[int]


class ParticipantIn(SQLModel):
    worker_id: str
    hit_id: str
    assignment_id: str
    platform: str


class ParticipantOut(SQLModel):
    worker_id: str
    status: str
    condition: str
    data_id: Optional[int]
    start_time: Optional[datetime]
    end_time: Optional[datetime]


class ParticipantDataIn(SQLModel):
    worker_id: str
    hit_id: Optional[str]  # study_id
    assignment_id: Optional[str]  # session_id
    platform: Optional[str]  # prolific or mturk or cloudresearch
    condition: Optional[str]
    start_time: Optional[datetime]
    json_data: List[Dict]


    class Config:
        arbitrary_types_allowed = True


class Data(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    participant: Optional[Participant] = Relationship(
        sa_relationship_kwargs={"uselist": False}, back_populates="data"
    )
    worker_id: Optional[str]
    condition: Optional[str]
    json_data: List[Dict] = Field(sa_column=Column(JSON))

    # Needed for Column(JSON)
    class Config:
        arbitrary_types_allowed = True


class ExperimentConfiguration(SQLModel):
    worker_id: str
    status: str
    condition: str
    data_id: Optional[int]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    debug_mode: bool = False
    estimated_task_duration: str = "15 minutes"
    compensation: str = "$2.50"
    experiment_title: str = "Example experiment"
    experiment_name: str = "example_experiment"
    version_date: str = "2023-10-21"
    open_tags: str = "[["
    close_tags: str = "]]"
    stimulus_width: int = 400
    num_stimuli: int = 2
    logrocket_id: str
    intertrial_interval: int
    stimulus_height: int
    slider_width: int


Participant.update_forward_refs()
ParticipantUpdate.update_forward_refs()
Data.update_forward_refs()
