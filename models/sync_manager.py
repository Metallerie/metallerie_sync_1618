import psycopg2

class SyncManager:
    @staticmethod
    def _get_connection(dbname):
        """
        Récupère une connexion à la base spécifiée.
        """
        return psycopg2.connect(
            dbname=dbname,
            user='odoo',
            password='0625159120',
            host='localhost',
            port='5432'
        )

    @staticmethod
    def run_global_sync():
        """
        Orchestrateur de synchronisation pour tous les modèles.
        """
        from .sync_company import SyncCompany
        SyncCompany.sync_v16_to_v18()
        # Ajouter d'autres appels à des synchronisations ici (e.g., produits, partenaires, etc.)
        print("Synchronisation globale terminée.")
