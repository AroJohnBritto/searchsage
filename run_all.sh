#!/bin/bash

# Start FastAPI backend
uvicorn backend.main:app --reload &

# Point the local Streamlit run at the local backend, not production
export SEARCHSAGE_BACKEND_URL="http://localhost:8000"

sleep 2
streamlit run app/ui.py
