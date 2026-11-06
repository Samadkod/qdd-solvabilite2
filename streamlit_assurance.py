"""Ancienne entrée de la version « assurance », gardée pour que son lien Streamlit continue de fonctionner.

L'application est désormais unique : tout est dans streamlit_app.py.
"""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("streamlit_app.py")), run_name="__main__")
