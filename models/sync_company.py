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
        Synchronise les sociétés de la V16 vers la V18 en utilisant les champs de la V18 comme référence.
        """
        _logger.info("Démarrage de la synchronisation des sociétés (V16 → V18)")

        source_conn = SyncManager._get_connection('1-metal-odoo16')  # Base V16
        target_conn = SyncManager._get_connection('1-metal-odoo18')  # Base V18

        try:
            source_cursor = source_conn.cursor()
            target_cursor = target_conn.cursor()

            # Récupérer les champs disponibles dans la table res_company de V18
            target_cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'res_company'
            """)
            target_columns = {row[0] for row in target_cursor.fetchall()}

            _logger.info(f"Champs disponibles dans la V18 : {target_columns}")

            # Identifier les champs communs entre V16 et V18
            source_cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'res_company'
            """)
            source_columns = {row[0] for row in source_cursor.fetchall()}

            common_columns = target_columns.intersection(source_columns)
            _logger.info(f"Champs communs entre V16 et V18 : {common_columns}")

            # Préparer les champs pour la requête SQL
            fields_to_sync = ', '.join(common_columns)

            # Extraction des données depuis la V16
            source_cursor.execute(f"""
                SELECT {fields_to_sync}
                FROM res_company
            """)
            companies = source_cursor.fetchall()
            _logger.info(f"{len(companies)} sociétés trouvées dans la base V16")

            for company in companies:
                company_data = dict(zip(common_columns, company))

                # Vérification si la société existe dans la V18
                target_cursor.execute("""
                    SELECT id FROM res_company WHERE id = %s
                """, (company_data['id'],))
                existing_company = target_cursor.fetchone()

                if existing_company:
                    # Mise à jour dynamique
                    set_clause = ', '.join([f"{col} = %s" for col in common_columns if col != 'id'])
                    values = [company_data[col] for col in common_columns if col != 'id'] + [company_data['id']]
                    _logger.info(f"Mise à jour de la société ID {company_data['id']}")
                    target_cursor.execute(f"""
                        UPDATE res_company
                        SET {set_clause}
                        WHERE id = %s
                    """, values)
                else:
                    # Insertion dynamique
                    columns_clause = ', '.join(common_columns)
                    placeholders = ', '.join(['%s'] * len(common_columns))
                    values = [company_data[col] for col in common_columns]
                    _logger.info(f"Insertion de la société ID {company_data['id']}")
                    target_cursor.execute(f"""
                        INSERT INTO res_company ({columns_clause})
                        VALUES ({placeholders})
                    """, values)

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

