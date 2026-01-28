# controllers/contacts_controller.py
from fastapi import UploadFile, HTTPException
import tempfile, os
from services.contacts_sync_service import sync_contactos_from_outlook_csv

def sync_contactos_controller(file: UploadFile, team_id: int, session, dry_run: bool = False):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Subí un .csv exportado de Outlook")

    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, file.filename)
        with open(path, "wb") as f:
            f.write(file.file.read())

        return sync_contactos_from_outlook_csv(
            session=session,
            team_id=team_id,
            csv_path=path,
            dry_run=dry_run,
        )
