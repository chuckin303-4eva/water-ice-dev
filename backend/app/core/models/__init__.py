"""SQLAlchemy models for the core (industry-independent) platform.

Documents, reviews, opportunities, resource_listings, tasks, and
settings are designed in docs/DATABASE.md but intentionally not modeled
yet -- they arrive with the migration for the phase that actually needs
them.
"""

from app.core.models import associations  # noqa: F401
from app.core.models.brand import Brand  # noqa: F401
from app.core.models.competitor import Competitor  # noqa: F401
from app.core.models.geography import City, County, State  # noqa: F401
from app.core.models.host_business import HostBusiness  # noqa: F401
from app.core.models.invoice import Invoice  # noqa: F401
from app.core.models.location import Location  # noqa: F401
from app.core.models.location_call_note import LocationCallNote  # noqa: F401
from app.core.models.organization import Organization  # noqa: F401
from app.core.models.permission import Permission  # noqa: F401
from app.core.models.photo import Photo  # noqa: F401
from app.core.models.refresh_run import RefreshRun  # noqa: F401
from app.core.models.role import Role  # noqa: F401
from app.core.models.subscription import Subscription  # noqa: F401
from app.core.models.update_log import UpdateLog  # noqa: F401
from app.core.models.user import User  # noqa: F401
from app.core.models.validation_queue import ValidationQueue  # noqa: F401
