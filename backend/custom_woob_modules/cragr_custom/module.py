import sys
sys.path.insert(0, '/root/.local/share/woob/modules/3.7')

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
