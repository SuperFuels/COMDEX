from backend.modules.photonlang.importer import install
install()
from backend.modules.photonlang.runtime.traceback_enricher import install as tb_install
tb_install()

import sys; sys.path.insert(0, "backend/tests")
import demo_error
demo_error.oops(3)