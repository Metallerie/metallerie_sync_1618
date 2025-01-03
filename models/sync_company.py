from odoo import models, fields, api
from .sync_manager import SyncManager

class SyncCompany(models.Model):
    _name = 'metallerie.sync.company'
    _description = 'Synchronisation unidirectionnelle des sociétés (V16 → V18)'

    name = fields.Char(string="Nom", default="Synchronisation des Sociétés")

    @staticmethod
    def sync_v16_to_v18():
        """
        Synchronise les sociétés de la V16 vers la V18 en conservant les IDs et en excluant les champs calculés.
        """
        source_conn = SyncManager._get_connection('1-metal-odoo16')  # Base V16
        target_conn = SyncManager._get_connection('1-metal-odoo18')  # Base V18

        try:
            source_cursor = source_conn.cursor()
            target_cursor = target_conn.cursor()

            # Extraction des données dans la V16 (exclure les champs calculés comme street)
            source_cursor.execute("""
                SELECT id, name,  email, phone, write_date, currency_id
                FROM res_company
            """)
            companies = source_cursor.fetchall()

            for company in companies:
                (company_id, name, country_id, email, phone, mobile, write_date, currency_id) = company

                # Vérifier si le country_id existe dans la base cible
                if country_id:
                    target_cursor.execute("SELECT id FROM res_country WHERE id = %s", (country_id,))
                    if not target_cursor.fetchone():
                        country_id = None  # Si le pays n'existe pas, définir comme None

                # Vérifier si le currency_id existe dans la base cible
                if currency_id:
                    target_cursor.execute("SELECT id FROM res_currency WHERE id = %s", (currency_id,))
                    if not target_cursor.fetchone():
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
                        target_cursor.execute("""
                            UPDATE res_company
                            SET name = %s,  
                                email = %s, phone = %s,  write_date = %s, currency_id = %s
                            WHERE id = %s
                        """, (name,  email, phone,  write_date, currency_id, company_id))
                else:
                    # Insertion avec l'ID de la V16
                    target_cursor.execute("""
                        INSERT INTO res_company (id, name,  email, phone,  write_date, currency_id)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (company_id, name,  email, phone,  write_date, currency_id))

            target_conn.commit()
        except Exception as e:
            target_conn.rollback()
            raise e
        finally:
            source_cursor.close()
            target_cursor.close()
            source_conn.close()
            target_conn.close()
