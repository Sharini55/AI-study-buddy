import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from utils.persistence import SessionLocal, User, Workspace, SourceFile, SourceImage, StudyGuide, QuizAttempt

def render_db_inspector_tab():
    """Renders a beautiful, read-only visual spreadsheet audit view of active SQLite tables."""
    st.subheader("🕵️‍♂️ Database Inspector")
    st.caption("This utility queries your local SQLite file and renders rows as spreadsheets, matching Airtable's schema view.")
    
    db: Session = SessionLocal()
    try:
        table_selection = st.selectbox(
            "Select Table to Audit",
            ["Users", "Workspaces", "Source Files", "Source Images", "Study Guides", "Quiz Attempts"]
        )
        
        st.divider()
        
        if table_selection == "Users":
            records = db.query(User).all()
            if not records:
                st.info("No registered users inside SQL yet.")
            else:
                data = [{"Username": u.username, "Salted Password Hash": u.password_hash, "Created At": u.created_at} for u in records]
                st.dataframe(pd.DataFrame(data), use_container_width=True)
                
        elif table_selection == "Workspaces":
            records = db.query(Workspace).all()
            if not records:
                st.info("No student workspaces created yet.")
            else:
                data = [{"ID": w.id, "Owner (Username)": w.user_id, "Subject Workspace": w.subject_name, "Created At": w.created_at} for w in records]
                st.dataframe(pd.DataFrame(data), use_container_width=True)
                
        elif table_selection == "Source Files":
            records = db.query(SourceFile).all()
            if not records:
                st.info("No documents or text material indexed yet.")
            else:
                data = [{"ID": f.id, "Workspace ID": f.workspace_id, "File Name": f.name, "File Type": f.file_type, "MD5 Hash": f.file_hash, "Character Count": len(f.content_text), "Created At": f.created_at} for f in records]
                st.dataframe(pd.DataFrame(data), use_container_width=True)
                
        elif table_selection == "Source Images":
            records = db.query(SourceImage).all()
            if not records:
                st.info("No multimodal slide images indexed.")
            else:
                data = [{"ID": img.id, "Source File ID": img.source_file_id, "Label": img.label, "Hard Drive Location": img.storage_path, "Mime Type": img.mime_type} for img in records]
                st.dataframe(pd.DataFrame(data), use_container_width=True)
                
        elif table_selection == "Study Guides":
            records = db.query(StudyGuide).all()
            if not records:
                st.info("No study guides generated yet.")
            else:
                data = [{"ID": sg.id, "Workspace ID": sg.workspace_id, "Title": sg.title, "Length (Chars)": len(sg.content_md), "Created At": sg.created_at} for sg in records]
                st.dataframe(pd.DataFrame(data), use_container_width=True)
                
        elif table_selection == "Quiz Attempts":
            records = db.query(QuizAttempt).all()
            if not records:
                st.info("No quiz scores captured yet.")
            else:
                data = [{"ID": q.id, "Workspace ID": q.workspace_id, "Score (%)": f"{q.score}%", "Created At": q.created_at} for q in records]
                st.dataframe(pd.DataFrame(data), use_container_width=True)
                
    except Exception as e:
        st.error(f"Error querying active database session: {str(e)}")
    finally:
        db.close()