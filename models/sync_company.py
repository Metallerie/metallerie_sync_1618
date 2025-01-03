from odoo import models, fields, api
from .sync_manager import SyncManager
import logging

_logger = logging.getLogger(__name__)

class SyncCompany(models.Model):
    _name = 'metallerie.sync.company'
    _description = 'Synchronisation unidirectionnelle des sociétés (V16 → V18)'

    name = fields.Char(string="Nom", default="Synchronisation des Sociétés")

    @staticmethod
    def _get_field_types(model_name, connection):
        """
        Récupère les types de champs pour un modèle donné dans la base cible.
        """
        cursor = connection.cursor()
        cursor.execute(f"""
            SELECT name, ttype 
            FROM ir_model_fields 
            WHERE model = %s
        """, (model_name,))
        return {row[0]: row[1] for row in cursor.fetchall()}

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
        Synchronise les sociétés de la V16 vers la V18 en détectant dynamiquement les champs simples.
        """
        _logger.info("Démarrage de la synchronisation des sociétés (V16 → V18)")

        source_conn = SyncManager._get_connection('1-metal-odoo16')  # Base V16
        target_conn = SyncManager._get_connection('1-metal-odoo18')  # Base V18

        try:
            # Récupération des types de champs dans la cible (V18)
            target_field_types = SyncCompany._get_field_types('res.company', target_conn)

            # Filtrer les champs simples dans la cible
            target_simple_fields = [
                name for name, ttype in target_field_types.items()
                if ttype in ['char', 'integer', 'float', 'boolean']
            ]

            fields_to_sync = target_simple_fields
            fields_to_sync_str = ', '.join(fields_to_sync)

            source_cursor = source_conn.cursor()
            target_cursor = target_conn.cursor()

            # Extraction des données dans la V16
            source_cursor.execute(f"""
                SELECT {fields_to_sync_str}
                FROM res_company
            """)
            companies = source_cursor.fetchall()
            _logger.info(f"{len(companies)} sociétés trouvées dans la base V16")

            for company in companies:
                company_data = dict(zip(fields_to_sync, company))

                # Vérification et ajustement des champs avant synchronisation
                for field in fields_to_sync:
                    company_data[field] = SyncCompany._check_conditions(
                        field, company_data.get(field), target_cursor
                    )

                # Vérification si la société existe dans la V18
                target_cursor.execute("""
                    SELECT id FROM res_company WHERE id = %s
                """, (company_data['id'],))
                existing_company = target_cursor.fetchone()

                if existing_company:
                    # Mise à jour dynamique
                    set_clause = ', '.join([f"{col} = %s" for col in fields_to_sync if col != 'id'])
                    values = [company_data[col] for col in fields_to_sync if col != 'id'] + [company_data['id']]
                    _logger.info(f"Mise à jour de la société ID {company_data['id']}")
                    target_cursor.execute(f"""
                        UPDATE res_company
                        SET {set_clause}
                        WHERE id = %s
                    """, values)
                else:
                    # Insertion dynamique
                    columns_clause = ', '.join(fields_to_sync)
                    placeholders = ', '.join(['%s'] * len(fields_to_sync))
                    values = [company_data[col] for col in fields_to_sync]
                    _logger.info(f"Insertion de la société ID {company_data['id']}")
                    target_cursor.execute(f"""
                        INSERT INTO res_company ({columns_clause})
                        VALUES ({placeholders})
                    """, values)

            target_conn.commit()
            _logger.info("Synchronisation dynamique terminée avec succès")
        except Exception as e:
            _logger.error("Erreur lors de la synchronisation", exc_info=True)
            target_conn.rollback()
            raise e
        finally:
            source_cursor.close()
            target_cursor.close()
            source_conn.close()
            target_conn.close()
