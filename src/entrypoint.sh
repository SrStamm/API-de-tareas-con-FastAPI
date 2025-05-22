#!/bin/bash

echo "Starting FastAPI application..."

uvicorn main:app --port 8000 --reload