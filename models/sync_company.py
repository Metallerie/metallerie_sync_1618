from odoo import models, api
import psycopg2

class SyncCompany(models.Model):
    _name = 'metallerie.sync.company'
    _description = 'Synchronisation unidirectionnelle des sociétés (V16 → V18)'

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
    def sync_v16_to_v18():
        """
        Synchronise les sociétés de la V16 vers la V18 en utilisant les champs de la V18 comme référence.
        """
        source_conn = SyncCompany._get_connection('1-metal-odoo16')  # Base V16
        target_conn = SyncCompany._get_connection('1-metal-odoo18')  # Base V18

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

            # Identifier les champs communs entre V16 et V18
            source_cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'res_company'
            """)
            source_columns = {row[0] for row in source_cursor.fetchall()}

            common_columns = target_columns.intersection(source_columns)

            # Préparer les champs pour la requête SQL
            fields_to_sync = ', '.join(common_columns)

            # Extraction des données depuis la V16
            source_cursor.execute(f"""
                SELECT {fields_to_sync}
                FROM res_company
            """)
            companies = source_cursor.fetchall()

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
                    target_cursor.execute(f"""
                        INSERT INTO res_company ({columns_clause})
                        VALUES ({placeholders})
                    """, values)

            target_conn.commit()
        except Exception as e:
            target_conn.rollback()
            raise e
        finally:
            source_cursor.close()
            target_cursor.close()
            source_conn.close()
            target_conn.close()
