async def _fetch_woob_transactions(
    bank_name: str,
    bank_website: str | None,
    login: str,
    password: str,
    days_back: int,
) -> list[dict[str, Any]]:
    """
    Fetch transactions using Woob - using working approach from user example.
    """
    from datetime import datetime
    from datetime import timedelta as td
    from woob.core import Woob
    
    transactions: list[dict[str, Any]] = []
    
    woob = Woob()
    
    # Build website URL from region code (ca-toulouse -> www.ca-toulouse31.fr)
    website_url = bank_website
    if bank_website and not bank_website.startswith('www.'):
        # Convert region code to URL format
        website_url = f"www.{bank_website}.fr"
    
    # Load backend with params (working approach)
    backend = woob.load_backend(
        bank_name,
        'bank_sync',
        params={
            'website': website_url,
            'login': login,
            'password': password,
        }
    )
    
    # Get browser and login
    browser = backend.browser
    browser.do_login()
    browser.location(browser.accounts_url)
    
    # Fetch accounts and transactions using iter_accounts/iter_history
    since_date = datetime.now() - td(days=days_back)
    
    for account in backend.iter_accounts():
        for history in backend.iter_history(account):
            if history.date < since_date:
                continue
            
            transactions.append({
                "date": history.date.date(),
                "amount": float(history.amount),
                "raw_label": history.label or history.raw or "Unknown",
                "currency": account.currency or "EUR",
            })
    
    backend.deinit()
    woob.deinit()
    
    return transactions
