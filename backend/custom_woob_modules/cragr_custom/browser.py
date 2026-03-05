import sys
sys.path.insert(0, '/root/.local/share/woob/modules/3.7')

from woob_modules.cragr.browser import CreditAgricoleBrowser
from .pages import AccountsPage


class CragrCustomBrowser(CreditAgricoleBrowser):
    accounts_page = CreditAgricoleBrowser.accounts_page
    accounts_page.klass = AccountsPage
