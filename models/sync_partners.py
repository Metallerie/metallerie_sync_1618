from odoo import models, fields, api
from .sync_manager import SyncManager
import logging

_logger = logging.getLogger(__name__)

class SyncPartner(models.Model):
    _name = 'metallerie.sync.partner'
    _description = 'Synchronisation unidirectionnelle des partenaires (V16 → V18)'

    name = fields.Char(string="Nom", default="Synchronisation des Partenaires")

    @staticmethod
    def _get_field_types(model_name, cursor):
        """
        Récupère les types de champs pour un modèle donné dans la base cible.
        """
        cursor.execute(f"""
            SELECT name, ttype 
            FROM ir_model_fields 
            WHERE model = %s
        """, (model_name,))
        return {row[0]: row[1] for row in cursor.fetchall()}

    @staticmethod
    def _check_conditions(field_name, value, cursor):
        """
        Vérifie les conditions dynamiques pour la synchronisation d'un champ.
        """
        if field_name == 'currency_id':
            cursor.execute("SELECT id FROM res_currency WHERE id = %s", (value,))
            if cursor.fetchone():
                return value
            else:
                _logger.warning(f"Condition échouée pour {field_name}: valeur {value} introuvable")
                return None
        elif field_name == 'company_id':
            cursor.execute("SELECT id FROM res_company WHERE id = %s", (value,))
            if cursor.fetchone():
                return value
            else:
                _logger.warning(f"Condition échouée pour {field_name}: valeur {value} introuvable")
                return None
        return value

    @staticmethod
    def sync_v16_to_v18():
        """
        Synchronise les partenaires de la V16 vers la V18 en détectant dynamiquement les champs simples.
        """
        _logger.info("Démarrage de la synchronisation des partenaires (V16 → V18)")

        source_cursor = SyncManager._get_cursor('1-metal-odoo16')  # Curseur V16
        target_cursor = SyncManager._get_cursor('1-metal-odoo18')  # Curseur V18

        try:
            field_types = SyncPartner._get_field_types('res.partner', target_cursor)
            simple_fields = [name for name, ttype in field_types.items() if ttype in ['char', 'integer', 'float', 'boolean']]

            source_cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'res_partner'
            """)
            source_columns = {row[0] for row in source_cursor.fetchall()}

            common_fields = [field for field in simple_fields if field in source_columns]
            _logger.info(f"Champs communs détectés : {common_fields}")

            source_cursor.execute(f"""
                SELECT {', '.join(common_fields)}
                FROM res_partner
            """)
            partners = source_cursor.fetchall()
            _logger.info(f"{len(partners)} partenaires trouvés dans la base V16")

            for partner in partners:
                partner_data = dict(zip(common_fields, partner))

                # Vérifier si les champs sont valides et compatibles
                partner_data = {
                    key: SyncPartner._check_conditions(key, value, target_cursor)
                    for key, value in partner_data.items()
                    if key in common_fields and value is not None
                }

                target_cursor.execute("""
                    SELECT id FROM res_partner WHERE id = %s
                """, (partner_data.get('id'),))
                existing_partner = target_cursor.fetchone()

                if existing_partner:
                    set_clause = ', '.join([f"{col} = %s" for col in partner_data.keys() if col != 'id'])
                    values = [partner_data[col] for col in partner_data.keys() if col != 'id'] + [partner_data['id']]
                    _logger.info(f"Mise à jour du partenaire ID {partner_data['id']}")
                    target_cursor.execute(f"""
                        UPDATE res_partner
                        SET {set_clause}
                        WHERE id = %s
                    """, values)
                else:
                    columns_clause = ', '.join(partner_data.keys())
                    placeholders = ', '.join(['%s'] * len(partner_data))
                    values = [partner_data[col] for col in partner_data.keys()]
                    _logger.info(f"Insertion du partenaire ID {partner_data.get('id')}")
                    target_cursor.execute(f"""
                        INSERT INTO res_partner ({columns_clause})
                        VALUES ({placeholders})
                    """, values)

            target_cursor.commit()
            _logger.info("Synchronisation dynamique terminée avec succès")
        except Exception as e:
            _logger.error("Erreur lors de la synchronisation", exc_info=True)
            target_cursor.rollback()
            raise e
        finally:
            source_cursor.close()
            target_cursor.close()
