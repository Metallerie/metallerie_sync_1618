from odoo import models, fields, api
from .sync_manager import SyncManager
import logging

_logger = logging.getLogger(__name__)

class SyncCompany(models.Model):
    _name = 'metallerie.sync.company'
    _description = 'Synchronisation unidirectionnelle des sociétés (V16 → V18)'

    name = fields.Char(string="Nom", default="Synchronisation des Sociétés")

    @staticmethod
    def sync_v16_to_v18():
        """
        Synchronise les sociétés de la V16 vers la V18 en conservant les IDs et en excluant les champs calculés.
        """
        _logger.info("Démarrage de la synchronisation des sociétés (V16 → V18)")

        source_conn = SyncManager._get_connection('1-metal-odoo16')  # Base V16
        target_conn = SyncManager._get_connection('1-metal-odoo18')  # Base V18

        try:
            source_cursor = source_conn.cursor()
            target_cursor = target_conn.cursor()

            # Extraction des données dans la V16 (exclure les champs calculés comme street)
            _logger.info("Extraction des données depuis la base V16")
            source_cursor.execute("""
                SELECT id, name, email, phone, write_date, currency_id
                FROM res_company
            """)
            companies = source_cursor.fetchall()
            _logger.info(f"{len(companies)} sociétés trouvées dans la base V16")

            for company in companies:
                (company_id, name, email, phone, write_date, currency_id) = company
                _logger.debug(f"Traitement de la société ID {company_id} : {name}")

                # Vérifier si le currency_id existe dans la base cible
                if currency_id:
                    target_cursor.execute("SELECT id FROM res_currency WHERE id = %s", (currency_id,))
                    if not target_cursor.fetchone():
                        _logger.warning(f"Devise {currency_id} non trouvée, définition à None")
                        currency_id = None  # Si la devise n'existe pas, définir comme None

                # Vérification si la société existe dans la V18
                target_cursor.execute("""
                    SELECT id, write_date FROM res_company WHERE id = %s
                """, (company_id,))
                existing_company = target_cursor.fetchone()

                if existing_company:
                    # Mise à jour si la donnée source est plus récente
                    existing_write_date = existing_company[1]
                    if write_date > existing_write_date:
                        _logger.info(f"Mise à jour de la société ID {company_id}")
                        target_cursor.execute("""
                            UPDATE res_company
                            SET name = %s, email = %s, phone = %s, write_date = %s, currency_id = %s
                            WHERE id = %s
                        """, (name, email, phone, write_date, currency_id, company_id))
                else:
                    # Insertion avec l'ID de la V16
                    _logger.info(f"Insertion de la société ID {company_id}")
                    target_cursor.execute("""
                        INSERT I
