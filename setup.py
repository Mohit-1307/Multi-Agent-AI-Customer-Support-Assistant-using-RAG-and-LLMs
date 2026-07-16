#!/usr/bin/env python3
"""
TechMart AI Support — One-time Setup Script
Handles: DB creation, admin user, and FAISS index building
"""

import sys
import os
import gc

# Memory optimization — must be FIRST before any imports
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["MALLOC_TRIM_THRESHOLD_"] = "100000"


def step1_check_env():

    print("\n📄 Checking .env file...")

    if not os.path.exists(".env"):

        if os.path.exists(".env.example"):

            import shutil

            shutil.copy(".env.example", ".env")

            print("✅ Created .env from .env.example")

            print("⚠️ Please add your GROQ_API_KEY to .env before starting the server.")

        else:

            print("⚠️ No .env file found. Create one from .env.example")

    else:

        print("✅ .env file found")


def step2_create_database():

    print("\n📦 Creating database tables...")

    try:

        from backend.database.db import create_tables

        create_tables()

        print("✅ Database tables created")

        return True

    except Exception as e:

        print(f"❌ Database error: {e}")

        print("Check your DATABASE_URL in .env")

        sys.exit(1)


def step3_create_admin():

    print("\n👤 Creating admin user...")

    try:

        from backend.database.db import SessionLocal, User

        from backend.api.auth import hash_password

        db = SessionLocal()

        admin = db.query(User).filter(User.email == "admin@techmart.com").first()

        if not admin:

            admin = User(
                name="Admin",
                email="admin@techmart.com",
                password_hash=hash_password("admin123"),
                is_admin=True,
            )

            db.add(admin)

            db.commit()

            print("✅ Admin user created")

            print("Email: admin@techmart.com")

            print("Password: admin123")

        else:

            print("✅ Admin user already exists")

        db.close()

    except Exception as e:

        print(f"❌ User creation error: {e}")


def step4_build_index():

    print("\n🔍 Building knowledge base index...")

    print("⏳ This may take 3-5 minutes. Please wait and do NOT close the terminal.\n")

    gc.collect()

    from pathlib import Path
    import pickle
    import numpy as np

    # Load & chunk files
    kb_dir = Path("knowledge_base")

    txt_files = sorted(kb_dir.glob("*.txt"))

    if not txt_files:

        print("❌ No .txt files found in knowledge_base/ directory.")

        return

    print(f"   Found {len(txt_files)} knowledge base files\n")

    all_chunks = []

    file_stats = {}

    for txt_path in txt_files:

        try:

            # Try multiple encodings for Windows compatibility
            text = None

            for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:

                try:

                    text = txt_path.read_text(encoding=enc, errors="ignore")

                    break

                except Exception:

                    continue

            if not text:

                print(f"⚠️ Could not read: {txt_path.name}")

                continue

            # Chunk the text
            chunk_size = 300

            overlap = 30

            file_chunks = []

            for i in range(0, len(text), chunk_size - overlap):

                chunk = text[i : i + chunk_size].strip()

                if len(chunk) > 50:  # skip tiny chunks

                    file_chunks.append(
                        {
                            "text": chunk,
                            "source": txt_path.stem,
                            "chunk_id": len(all_chunks) + len(file_chunks),
                        }
                    )

            all_chunks.extend(file_chunks)

            file_stats[txt_path.stem] = {
                "chunks": len(file_chunks),
                "file_size_bytes": txt_path.stat().st_size,
            }

            print(f"✅ {txt_path.name:<35} {len(file_chunks)} chunks")

            # Free memory after each file
            del text

            del file_chunks

            gc.collect()

        except MemoryError:

            print(f"⚠️ Skipped {txt_path.name} — not enough RAM")

            gc.collect()

            continue

        except Exception as e:

            print(f"⚠️ Error loading {txt_path.name}: {e}")

            continue

    if not all_chunks:

        print("\n❌ No chunks loaded. Check knowledge_base/ directory.")

        return

    total_chunks = len(all_chunks)

    print(f"\nTotal chunks loaded: {total_chunks}")

    gc.collect()

    # Generate embeddings
    print("\nLoading embedding model...")

    try:

        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("all-MiniLM-L6-v2")

        gc.collect()

    except Exception as e:

        print(f"❌ Failed to load embedding model: {e}")

        return

    print("Generating embeddings (batch size = 2)...")

    texts = [c["text"] for c in all_chunks]

    embeddings_list = []

    for i in range(0, len(texts), 2):

        batch = texts[i : i + 2]

        try:

            emb = model.encode(
                batch,
                batch_size=2,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )

            embeddings_list.append(emb.astype(np.float32))

            # Progress update every 20 chunks
            if i % 20 == 0:

                done = min(i + 2, total_chunks)

                bar = "█" * int((done / total_chunks) * 30)

                space = "░" * (30 - len(bar))

                pct = int((done / total_chunks) * 100)

                print(f"[{bar}{space}] {pct}% ({done}/{total_chunks})", end="\r")

            gc.collect()

        except MemoryError:

            print(f"\n⚠️ Memory error at batch {i} — skipping")

            gc.collect()

            continue

        except Exception as e:

            print(f"\n⚠️ Embedding error at batch {i}: {e}")

            continue

    print(f"\n✅ Embeddings generated: {len(embeddings_list)} batches")

    # Cleanup model from RAM
    del model

    del texts

    gc.collect()

    if not embeddings_list:

        print("❌ No embeddings generated.")

        return

    # Build FAISS index
    print("\n   Building FAISS index...")

    try:

        import faiss

        embeddings = np.vstack(embeddings_list).astype(np.float32)

        del embeddings_list

        gc.collect()

        dim = embeddings.shape[1]

        index = faiss.IndexFlatIP(dim)

        index.add(embeddings)

        del embeddings

        gc.collect()

        print(f"✅ FAISS index built: {index.ntotal} vectors, dim={dim}")

    except Exception as e:

        print(f"❌ FAISS error: {e}")

        return

    # Save index to disk
    print("\n Saving index to disk...")

    try:

        index_dir = Path("backend/vectorstore/faiss_index")

        index_dir.mkdir(parents=True, exist_ok=True)

        faiss.write_index(index, str(index_dir / "faiss.index"))

        with open(index_dir / "chunks.pkl", "wb") as f:

            pickle.dump(all_chunks, f)

        print(f"✅ Index saved to {index_dir}")

    except Exception as e:

        print(f"❌ Failed to save index: {e}")

        return

    # Update DB records
    try:

        from backend.database.db import SessionLocal, KnowledgeBaseDoc

        db = SessionLocal()

        db.query(KnowledgeBaseDoc).delete()

        for filename, stats in file_stats.items():

            doc = KnowledgeBaseDoc(
                filename=filename,
                chunk_count=stats["chunks"],
                file_size_bytes=stats["file_size_bytes"],
            )

            db.add(doc)

        db.commit()

        db.close()

    except Exception as e:

        print(f"⚠️ DB record update skipped: {e}")

    print(f"\n✅ Index built: {total_chunks} chunks from {len(file_stats)} documents")


def main():

    print("=" * 60)

    print("  TechMart AI Support — Setup")

    print("=" * 60)

    step1_check_env()

    step2_create_database()

    step3_create_admin()

    step4_build_index()

    print("\n" + "=" * 60)

    print("✅ Setup Complete!")

    print("=" * 60)

    print("\nNext steps:")

    print("1. Start backend  → uvicorn backend.main:app --reload")

    print("2. Open new terminal → cd frontend && npm install && npm run dev")

    print("3. Open browser → http://localhost:3000")

    print("4. Login → admin@techmart.com / admin123")

    print("5. API docs → http://localhost:8000/docs")

    print("=" * 60)


if __name__ == "__main__":

    main()
