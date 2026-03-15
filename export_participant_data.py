# save_as: export_participant_data.py
from sqlmodel import Session, select
from database import engine
from models import Data
import os
import json
import csv

def export_participant_data(data_id, output_dir="exported_data"):
    """Export data for a specific participant."""
    with Session(engine) as session:
        data_row = session.exec(select(Data).where(Data.id == data_id)).first()
        if not data_row:
            print(f"No Data row found for id={data_id}")
            return False

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # pretty-print json_data to file
        json_file = os.path.join(output_dir, f"data_{data_id}.json")
        with open(json_file, "w") as f:
            json.dump(data_row.json_data, f, indent=2)

        # export flattened CSV (one row per trial)
        # Filter for face judgement task data only (exclude KAI survey data)
        rows = []
        for trial_data in data_row.json_data:
            # Skip KAI survey responses
            if "KAI_responses" in trial_data:
                continue
            # Include face judgement task trials (image-slider-response trials)
            if trial_data.get("trial_type") == "image-slider-response":
                rows.append(trial_data)
        
        if not rows:
            print(f"No face judgement task data found for data_id={data_id}")
            return False

        keys = set()
        for r in rows:
            keys.update(r.keys())
        keys = sorted(keys)
        
        csv_file = os.path.join(output_dir, f"data_{data_id}_trials.csv")
        with open(csv_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for r in rows:
                # string-encode any nested objects (e.g., responses)
                out = {k: (json.dumps(r[k]) if isinstance(r.get(k), (dict, list)) else r.get(k)) for k in keys}
                writer.writerow(out)

        print(f"Exported data for participant {data_id}")
        return True


def export_participant_survey_data(data_id, output_dir="exported_data"):
    """Export survey data for a specific participant."""
    with Session(engine) as session:
        data_row = session.exec(select(Data).where(Data.id == data_id)).first()
        if not data_row:
            print(f"No Data row found for id={data_id}")
            return False

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Filter for survey data (exclude face judgement task data)
        survey_rows = []
        kai_rows = []
        
        for trial_data in data_row.json_data:
            # Collect KAI survey responses
            if "KAI_responses" in trial_data:
                kai_rows.append(trial_data)
            # Collect other survey data (render-mustache-template trials with form_data)
            elif (trial_data.get("trial_type") == "render-mustache-template" and 
                  trial_data.get("form_data") and 
                  trial_data.get("experiment_phase") == "survey"):
                survey_rows.append(trial_data)
        
        # Export KAI survey data
        if kai_rows:
            kai_file = os.path.join(output_dir, f"data_{data_id}_kai_survey.csv")
            kai_keys = set()
            for r in kai_rows:
                kai_keys.update(r.keys())
                # Also include KAI response keys
                if "KAI_responses" in r:
                    kai_keys.update(r["KAI_responses"].keys())
            kai_keys = sorted(kai_keys)
            
            with open(kai_file, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=kai_keys)
                writer.writeheader()
                for r in kai_rows:
                    # string-encode any nested objects (e.g., responses)
                    out = {k: (json.dumps(r[k]) if isinstance(r.get(k), (dict, list)) else r.get(k)) for k in kai_keys}
                    writer.writerow(out)
            print(f"Exported KAI survey data for participant {data_id}")

        # Export other survey data
        if survey_rows:
            survey_file = os.path.join(output_dir, f"data_{data_id}_survey.csv")
            survey_keys = set()
            for r in survey_rows:
                survey_keys.update(r.keys())
            survey_keys = sorted(survey_keys)
            
            with open(survey_file, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=survey_keys)
                writer.writeheader()
                for r in survey_rows:
                    # string-encode any nested objects (e.g., responses)
                    out = {k: (json.dumps(r[k]) if isinstance(r.get(k), (dict, list)) else r.get(k)) for k in survey_keys}
                    writer.writerow(out)
            print(f"Exported survey data for participant {data_id}")

        if not kai_rows and not survey_rows:
            print(f"No survey data found for data_id={data_id}")
            return False

        return True

def export_all_participants():
    """Export data for all participants in the database."""
    with Session(engine) as session:
        # Get all data rows
        all_data = session.exec(select(Data)).all()
        
        if not all_data:
            print("No data found in database")
            # Clean up exported_data directory if it exists
            output_dir = "exported_data"
            if os.path.exists(output_dir):
                import shutil
                shutil.rmtree(output_dir)
                print(f"Cleaned up '{output_dir}' directory")
            return

        output_dir = "exported_data"
        os.makedirs(output_dir, exist_ok=True)
        
        # Export combined CSV for all participants
        all_rows = []
        all_keys = set()
        
        for data_row in all_data:
            # Filter for face judgement task data only
            for trial_data in data_row.json_data:
                # Skip KAI survey responses
                if "KAI_responses" in trial_data:
                    continue
                # Include face judgement task trials (image-slider-response trials)
                if trial_data.get("trial_type") == "image-slider-response":
                    # Add participant ID to the trial data
                    trial_data_with_participant = trial_data.copy()
                    trial_data_with_participant['participant_id'] = data_row.id
                    trial_data_with_participant['worker_id'] = data_row.worker_id
                    trial_data_with_participant['condition'] = data_row.condition
                    all_rows.append(trial_data_with_participant)
                    all_keys.update(trial_data_with_participant.keys())
        
        if not all_rows:
            print("No face judgement task data found for any participants")
            # Clean up exported_data directory if it exists
            if os.path.exists(output_dir):
                import shutil
                shutil.rmtree(output_dir)
                print(f"Cleaned up '{output_dir}' directory")
            return

        all_keys = sorted(all_keys)
        
        # Export individual participant files
        for data_row in all_data:
            export_participant_data(data_row.id, output_dir)
            export_participant_survey_data(data_row.id, output_dir)
        
        # Export combined file
        combined_csv = os.path.join(output_dir, "all_participants_trials.csv")
        with open(combined_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys)
            writer.writeheader()
            for r in all_rows:
                # string-encode any nested objects (e.g., responses)
                out = {k: (json.dumps(r[k]) if isinstance(r.get(k), (dict, list)) else r.get(k)) for k in all_keys}
                writer.writerow(out)

        print(f"Exported data for {len(all_data)} participants to '{output_dir}' directory")
        print(f"Combined data saved to '{combined_csv}'")


def export_all_participants_survey_data():
    """Export survey data for all participants in the database."""
    with Session(engine) as session:
        # Get all data rows
        all_data = session.exec(select(Data)).all()
        
        if not all_data:
            print("No data found in database")
            return

        output_dir = "exported_data"
        os.makedirs(output_dir, exist_ok=True)
        
        # Export combined KAI survey CSV for all participants
        all_kai_rows = []
        all_kai_keys = set()
        
        # Export combined survey CSV for all participants
        all_survey_rows = []
        all_survey_keys = set()
        
        for data_row in all_data:
            # Filter for survey data
            for trial_data in data_row.json_data:
                # Collect KAI survey responses
                if "KAI_responses" in trial_data:
                    # Add participant ID to the trial data
                    trial_data_with_participant = trial_data.copy()
                    trial_data_with_participant['participant_id'] = data_row.id
                    trial_data_with_participant['worker_id'] = data_row.worker_id
                    trial_data_with_participant['condition'] = data_row.condition
                    all_kai_rows.append(trial_data_with_participant)
                    all_kai_keys.update(trial_data_with_participant.keys())
                    # Also include KAI response keys
                    if "KAI_responses" in trial_data_with_participant:
                        all_kai_keys.update(trial_data_with_participant["KAI_responses"].keys())
                
                # Collect other survey data (render-mustache-template trials with form_data)
                elif (trial_data.get("trial_type") == "render-mustache-template" and 
                      trial_data.get("form_data") and 
                      trial_data.get("experiment_phase") == "survey"):
                    # Add participant ID to the trial data
                    trial_data_with_participant = trial_data.copy()
                    trial_data_with_participant['participant_id'] = data_row.id
                    trial_data_with_participant['worker_id'] = data_row.worker_id
                    trial_data_with_participant['condition'] = data_row.condition
                    all_survey_rows.append(trial_data_with_participant)
                    all_survey_keys.update(trial_data_with_participant.keys())
        
        # Export combined KAI survey file
        if all_kai_rows:
            all_kai_keys = sorted(all_kai_keys)
            combined_kai_csv = os.path.join(output_dir, "all_participants_kai_survey.csv")
            with open(combined_kai_csv, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=all_kai_keys)
                writer.writeheader()
                for r in all_kai_rows:
                    # string-encode any nested objects (e.g., responses)
                    out = {k: (json.dumps(r[k]) if isinstance(r.get(k), (dict, list)) else r.get(k)) for k in all_kai_keys}
                    writer.writerow(out)
            print(f"Combined KAI survey data saved to '{combined_kai_csv}'")

        # Export combined survey file
        if all_survey_rows:
            all_survey_keys = sorted(all_survey_keys)
            combined_survey_csv = os.path.join(output_dir, "all_participants_survey.csv")
            with open(combined_survey_csv, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=all_survey_keys)
                writer.writeheader()
                for r in all_survey_rows:
                    # string-encode any nested objects (e.g., responses)
                    out = {k: (json.dumps(r[k]) if isinstance(r.get(k), (dict, list)) else r.get(k)) for k in all_survey_keys}
                    writer.writerow(out)
            print(f"Combined survey data saved to '{combined_survey_csv}'")

        if not all_kai_rows and not all_survey_rows:
            print("No survey data found for any participants")
            return

        print(f"Exported survey data for {len(all_data)} participants to '{output_dir}' directory")

if __name__ == "__main__":
    # Export all participants when script is run
    export_all_participants()
