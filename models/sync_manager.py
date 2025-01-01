
from .sync_company import SyncCompany
from .sync_products import SyncProducts
from .sync_partners import SyncPartners

class SyncManager:
    @staticmethod
    def run_global_sync():
        SyncCompany.sync()
        SyncProducts.sync()
        SyncPartners.sync()
