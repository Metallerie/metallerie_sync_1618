
from odoo import models, api
from .sync_manager import SyncManager

class SyncCompany(models.Model):
    _name = 'metallerie.sync.company'
    _description = 'Synchronisation unidirectionnelle des sociétés (V16 → V18)'
    name = fields.Char(string="Nom", default="Synchronisation des Sociétés")
    @staticmethod
    def sync_v16_to_v18():
        """
        Synchronise les sociétés de la V16 vers la V18.
        """
        source_conn = SyncManager._get_connection('1-metal-odoo16')  # Base V16
        target_conn = SyncManager._get_connection('1-metal-odoo18')  # Base V18

        try:
            source_cursor = source_conn.cursor()
            target_cursor = target_conn.cursor()

            # Extraction des données dans la V16
            source_cursor.execute("""
                SELECT id, name, street, city, zip, country_id, email, phone, logo, write_date
                FROM res_company
            """)
            companies = source_cursor.fetchall()

            for company in companies:
                (company_id, name, street, city, zip_code, country_id, email, phone, logo, write_date) = company

                # Vérification si la société existe dans la V18
                target_cursor.execute("""
                    SELECT id, write_date FROM res_company WHERE name = %s
                """, (name,))
                existing_company = target_cursor.fetchone()

                if existing_company:
                    # Mise à jour si la donnée source est plus récente
                    existing_write_date = existing_company[1]
                    if write_date > existing_write_date:
                        target_cursor.execute("""
                            UPDATE res_company
                            SET street = %s, city = %s, zip = %s, country_id = %s, email = %s, phone = %s, logo = %s, write_date = %s
                            WHERE id = %s
                        """, (street, city, zip_code, country_id, email, phone, logo, write_date, existing_company[0]))
                else:
                    # Insertion d'une nouvelle société
                    target_cursor.execute("""
                        INSERT INTO res_company (name, street, city, zip, country_id, email, phone, logo, write_date)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (name, street, city, zip_code, country_id, email, phone, logo, write_date))

            target_conn.commit()
        except Exception as e:
            target_conn.rollback()
            raise e
        finally:
            source_cursor.close()
            target_cursor.close()
            source_conn.close()
            target_conn.close()
