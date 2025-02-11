#!/usr/bin/env python3
"""Runs the Uvicorn server for the FastAPI application."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.server:app", host="0.0.0.0", port=8003, reload=True)
