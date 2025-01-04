import psycopg2

class SyncManager:
    @staticmethod
    def _get_connection(dbname):
        """
        Récupère une connexion à la base spécifiée via la connexion interne Odoo.
        """
        try:
            import odoo
            registry = odoo.registry(dbname)
            return registry.cursor()
        except Exception as e:
            raise ConnectionError(f"Impossible de se connecter à la base de données {dbname}: {e}")

    @staticmethod
    def run_global_sync():
        """
        Orchestrateur de synchronisation pour tous les modèles.
        """
        from .sync_company import SyncCompany
        SyncCompany.sync_v16_to_v18()
        # Ajouter d'autres appels à des synchronisations ici (e.g., produits, partenaires, etc.)
        print("Synchronisation globale terminée.")
