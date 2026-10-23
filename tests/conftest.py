"""Configuración común de tests.

Perfiles de hypothesis: "ci" es determinista (misma semilla en cada ejecución) para que
los fallos sean reproducibles; "dev" explora más casos en local. Se elige con
HYPOTHESIS_PROFILE (por defecto "ci").
"""

import os

from hypothesis import settings

settings.register_profile("ci", max_examples=300, derandomize=True, deadline=None)
settings.register_profile("dev", max_examples=1000, deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "ci"))
