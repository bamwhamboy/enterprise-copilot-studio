"""Document ingestion pipeline: orchestrates storage + parsing + metadata.

Pure file-processing — no database knowledge. The service layer owns
persisting a Document row and its status transitions around these steps.
"""
