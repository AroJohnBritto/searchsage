#!/bin/bash

# Start FastAPI backend
uvicorn backend.main:app --reload &

# Start Streamlit frontend
sleep 2
streamlit run app/ui.py