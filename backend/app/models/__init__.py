# Import all models here so Alembic's autogenerate can see them
from app.models.base import Base  # noqa: F401
from app.models.user import User, UserRole  # noqa: F401
from app.models.user_site_assignment import UserSiteAssignment  # noqa: F401
from app.models.client import Client  # noqa: F401
from app.models.site import Site  # noqa: F401
from app.models.report import Report  # noqa: F401
from app.models.system_condition import SystemCondition  # noqa: F401
from app.models.file_record import FileRecord  # noqa: F401
from app.models.contact import Contact  # noqa: F401
from app.models.site_note import SiteNote  # noqa: F401
from app.models.lead import Lead  # noqa: F401
from app.models.service_item import ServiceItem  # noqa: F401
from app.models.quote import Quote  # noqa: F401
from app.models.quote_line_item import QuoteLineItem  # noqa: F401
from app.models.invoice import Invoice  # noqa: F401
from app.models.invoice_line_item import InvoiceLineItem  # noqa: F401
