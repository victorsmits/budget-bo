import sys
sys.path.insert(0, '/root/.local/share/woob/modules/3.7')

from woob.browser.elements import ItemElement, DictElement, method
from woob.browser.filters.json import Dict
from woob.browser.filters.standard import CleanText, Format, Map, Field, Coalesce, Eval
from woob.capabilities.bank import Account, AccountOwnerType
from woob.capabilities.base import NotAvailable

from woob_modules.cragr.pages import (
    AccountsPage as BaseAccountsPage,
    ACCOUNT_TYPES,
    ACCOUNT_OWNERSHIPS,
    float_to_decimal,
)


class AccountsPage(BaseAccountsPage):

    @method
    class get_main_account(ItemElement):
        klass = Account

        obj_id = CleanText(Dict("comptePrincipal/numeroCompte"))
        obj_number = CleanText(Dict("comptePrincipal/numeroCompte"))
        obj_currency = CleanText(Dict("comptePrincipal/idDevise"))
        obj__index = Dict("comptePrincipal/index")
        obj__category = Dict("comptePrincipal/grandeFamilleProduitCode", default=None)
        obj__id_element_contrat = CleanText(Dict("comptePrincipal/idElementContrat"))
        obj_ownership = Map(
            CleanText(Dict("comptePrincipal/rolePartenaireCalcule")),
            ACCOUNT_OWNERSHIPS,
            default=NotAvailable,
        )
        obj__fam_product_code = Dict("comptePrincipal/familleProduit/code", default=None)
        obj__fam_contract_code = Dict("comptePrincipal/sousFamilleProduit/code", default=None)

        def obj_owner_type(self):
            return self.page.get_owner_type()

        def obj_balance(self):
            balance = Dict("comptePrincipal/solde", default=NotAvailable)(self)
            if balance is not NotAvailable:
                return Eval(float_to_decimal, balance)(self)
            return NotAvailable

        def obj_label(self):
            if Field("owner_type")(self) == AccountOwnerType.PRIVATE:
                return CleanText(Dict("comptePrincipal/libelleProduit"))(self)
            return Format(
                "%s %s",
                CleanText(Dict("comptePrincipal/libelleProduit")),
                CleanText(Dict("comptePrincipal/libelleCompte", default="")),
            )(self)

        def obj_type(self):
            val = CleanText(Dict("comptePrincipal/typeProduit", default=""))(self)
            _type = ACCOUNT_TYPES.get(val, Account.TYPE_UNKNOWN)
            if _type == Account.TYPE_UNKNOWN:
                self.logger.warning('Untyped account: please add "%s" to ACCOUNT_TYPES.', val)
            return _type

    @method
    class iter_accounts(DictElement):
        # grandesFamilles est une liste -> on itère sur chaque famille puis ses elementsContrats
        item_xpath = "grandesFamilles"

        class item(DictElement):
            item_xpath = "elementsContrats"

            class item(ItemElement):
                klass = Account

                def condition(self):
                    # Ignorer les assurances
                    famille = Dict("grandeFamilleProduits", default="")(self)
                    return famille not in ("MES ASSURANCES", "VOS ASSURANCES")

                def obj_id(self):
                    produit = CleanText(Dict("libelleProduit", default=""))(self)
                    _type = ACCOUNT_TYPES.get(produit, Account.TYPE_UNKNOWN)
                    if _type in (
                        Account.TYPE_LOAN,
                        Account.TYPE_CONSUMER_CREDIT,
                        Account.TYPE_REVOLVING_CREDIT,
                        Account.TYPE_MORTGAGE,
                    ):
                        return CleanText(Dict("idElementContrat"))(self)
                    return CleanText(Dict("numeroCompte"))(self)

                obj_number = CleanText(Dict("numeroCompte"))
                obj_currency = CleanText(Dict("idDevise"))
                obj__index = Dict("index")
                obj__category = Coalesce(
                    Dict("grandeFamilleProduitCode", default=None),
                    Dict("sousFamilleProduit/niveau", default=None),
                    default=None,
                )
                obj__id_element_contrat = CleanText(Dict("idElementContrat"))
                obj_ownership = Map(
                    CleanText(Dict("rolePartenaireCalcule")),
                    ACCOUNT_OWNERSHIPS,
                    default=NotAvailable,
                )
                obj__fam_product_code = Dict("familleProduit/code", default=None)
                obj__fam_contract_code = Dict("sousFamilleProduit/code", default=None)

                def obj_owner_type(self):
                    return self.page.get_owner_type()

                def obj_label(self):
                    if Field("owner_type")(self) == AccountOwnerType.PRIVATE:
                        return CleanText(Dict("libelleProduit"))(self)
                    return Format(
                        "%s %s",
                        CleanText(Dict("libelleProduit")),
                        CleanText(Dict("libelleCompte", default="")),
                    )(self)

                def obj_type(self):
                    produit = CleanText(Dict("libelleProduit", default=""))(self)
                    _type = ACCOUNT_TYPES.get(produit, Account.TYPE_UNKNOWN)
                    if _type == Account.TYPE_LIFE_INSURANCE and "MANDAT CTO" in produit:
                        _type = Account.TYPE_MARKET
                    if _type == Account.TYPE_UNKNOWN:
                        self.logger.warning('Untyped account: "%s"', produit)
                    return _type
