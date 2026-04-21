"""Quick geometry sanity check — run from stormwater_app directory."""
import sys
sys.path.insert(0, ".")

from app.services.page_fit import BODY_HEIGHT_PT
from app.services.report_builder import _BODY_HEIGHT_PT

print(f"page_fit   BODY_HEIGHT_PT  = {BODY_HEIGHT_PT:.4f} pt")
print(f"report_builder _BODY_HEIGHT_PT = {_BODY_HEIGHT_PT:.4f} pt")
print(f"Match: {abs(BODY_HEIGHT_PT - _BODY_HEIGHT_PT) < 0.001}")
