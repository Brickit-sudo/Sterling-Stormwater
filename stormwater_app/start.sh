#!/bin/sh
unset STREAMLIT_SERVER_PORT
exec python -m streamlit run app.py \
  --server.port=8501 \
  --server.address=0.0.0.0 \
  --server.headless=true \
  --server.fileWatcherType=none
