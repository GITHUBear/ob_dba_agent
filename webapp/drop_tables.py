from webapp.database import SessionLocal
from webapp.schemas import *

if __name__ == '__main__':
    with SessionLocal() as db:
        db.query(Task).delete()
        db.query(Post).delete()
        db.query(Topic).delete()
        db.query(UploadedFile).delete()
        db.commit()
        print("Tables deleted")
        