from sqlmodel import SQLModel, create_engine, Session

DATABASE_URL = "postgresql://wsp_user:wsp123@localhost:5432/base_mdzinternet"

engine = create_engine(
    DATABASE_URL,
    echo=True
)

def get_session():
    with Session(engine) as session:
        yield session
