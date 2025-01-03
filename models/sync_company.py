from odoo import models, fields, api
from .sync_manager import SyncManager
import logging

_logger = logging.getLogger(__name__)

class SyncCompany(models.Model):
    _name = 'metallerie.sync.company'
    _description = 'Synchronisation unidirectionnelle des sociétés (V16 → V18)'

    name = fields.Char(string="Nom", default="Synchronisation des Sociétés")
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)

    @staticmethod
    def _check_conditions(field_name, value, target_cursor):
        """
        Vérifie les conditions dynamiques pour la synchronisation d'un champ.
        """
        if field_name == 'currency_id':
            # Vérifie si la devise existe dans la cible
            target_cursor.execute("SELECT id FROM res_currency WHERE id = %s", (value,))
            if target_cursor.fetchone():
                return value
            else:
                _logger.warning(f"Condition échouée pour {field_name}: valeur {value} introuvable")
                return None
        elif field_name == 'partner_id':
            # Vérifie si le partenaire existe dans la cible
            target_cursor.execute("SELECT id FROM res_partner WHERE id = %s", (value,))
            if target_cursor.fetchone():
                return value
            else:
                _logger.warning(f"Condition échouée pour {field_name}: valeur {value} introuvable")
                return None
        return value

    @staticmethod
    def sync_v16_to_v18():
        """
        Synchronise les sociétés de la V16 vers la V18 avec un système de conditions pour les champs.
        """
        _logger.info("Démarrage de la synchronisation des sociétés (V16 → V18)")

        source_conn = SyncManager._get_connection('1-metal-odoo16')  # Base V16
        target_conn = SyncManager._get_connection('1-metal-odoo18')  # Base V18

        try:
            source_cursor = source_conn.cursor()
            target_cursor = target_conn.cursor()

            # Extraction des données dans la V16
            source_cursor.execute("""
                SELECT id, name, partner_id, email, phone, currency_id
                FROM res_company
            """)
            companies = source_cursor.fetchall()
            _logger.info(f"{len(companies)} sociétés trouvées dans la base V16")

            for company in companies:
                (company_id, name, partner_id, email, phone, currency_id) = company

                # Appliquer les conditions
                partner_id = SyncCompany._check_conditions('partner_id', partner_id, target_cursor)
                currency_id = SyncCompany._check_conditions('currency_id', currency_id, target_cursor)

                # Vérification si la société existe dans la V18
                target_cursor.execute("""
                    SELECT id FROM res_company WHERE id = %s
                """, (company_id,))
                existing_company = target_cursor.fetchone()

                if existing_company:
                    # Mise à jour inconditionnelle avec gestion des champs conditionnels
                    _logger.info(f"Mise à jour de la société ID {company_id}")
                    target_cursor.execute("""
                        UPDATE res_company
                        SET name = %s, partner_id = %s, email = %s, phone = %s, currency_id = %s
                        WHERE id = %s
                    """, (name, partner_id, email, phone, currency_id, company_id))
                else:
                    # Insertion de la société
                    _logger.info(f"Insertion de la société ID {company_id}")
                    target_cursor.execute("""
                        INSERT INTO res_company (id, name, partner_id, email, phone, currency_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (company_id, name, partner_id, email, phone, currency_id))

            target_conn.commit()
            _logger.info("Synchronisation terminée avec succès")
        except Exception as e:
            _logger.error("Erreur lors de la synchronisation", exc_info=True)
            target_conn.rollback()
            raise e
        finally:
            source_cursor.close()
            target_cursor.close()
            source_conn.close()
            target_conn.close()
