import os
from dotenv import load_dotenv
from pydantic import BaseSettings

load_dotenv()


BASE_DIR = os.path.dirname(os.path.realpath(__file__))


class Settings(BaseSettings):
    # Private settings -- not seen by frontend
    app_name: str = "FastAPI Face Ratings"
    database_url: str = f"sqlite:///{os.path.join(BASE_DIR, 'database.db')}"
    num_images: int = 1  # = 10
    images_per_subject: int = 1  # = 5
    shuffle: bool = True
    allotted_time: int = 3600  # in seconds
    refresh_time: int = 300  # in seconds
    condition: str = "emotional" #emotional, professional, smart
    environment_type: str = "debug"
    admin_username: str = "username_to_be_set_in_env_file_not_here"
    admin_password: str = "password_to_be_set_in_env_file_not_here"

    # Public settings -- seen by frontend
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
    logrocket_id: str = "my-cool-experiment"
    intertrial_interval: int = 100
    stimulus_height: int = 400
    stimulus_width: int = 400
    slider_width: int = 600

    class Config:
        env_file = ".env"
