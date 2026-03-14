import sys
import os

# Try different possible woob modules paths
possible_paths = [
    '/root/.local/share/woob/modules/3.7',  # root user (build time)
    '/home/appuser/.local/share/woob/modules/3.7',  # appuser (production)
    '/app/.local/share/woob/modules/3.7',  # app directory
]

for path in possible_paths:
    if os.path.exists(path):
        sys.path.insert(0, path)
        break

from woob_modules.cragr.module import CreditAgricoleModule
from .browser import CragrCustomBrowser


class CragrCustomModule(CreditAgricoleModule):
    NAME = "cragr_custom"
    DESCRIPTION = "Crédit Agricole (patch API 2025)"
    MAINTAINER = "Victor Smits"
    EMAIL = ""
    VERSION = "1.0"

    BROWSER = CragrCustomBrowser

    def create_default_browser(self):
        region_website = self.config["website"].get()
        return self.create_browser(
            region_website,
            self.config["login"].get(),
            self.config["password"].get(),
        )
