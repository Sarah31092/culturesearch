from app.database import Base, engine
from app.rag import build_embeddings


Base.metadata.create_all(bind=engine)
count = build_embeddings()
print(f"ChromaDB 임베딩 저장 완료: {count}건")
