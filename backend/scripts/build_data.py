from app.database import Base, engine
from app.data_pipeline import load_database


Base.metadata.create_all(bind=engine)
count = load_database()
print(f"행사 데이터 저장 완료: {count}건")
