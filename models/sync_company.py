@staticmethod
def sync_v16_to_v18():
    _logger.info("Démarrage de la synchronisation des sociétés (V16 → V18)")

    source_conn = SyncManager._get_connection('1-metal-odoo16')  # Base V16
    target_conn = SyncManager._get_connection('1-metal-odoo18')  # Base V18

    try:
        # Récupération des types de champs dans la cible
        field_types = SyncCompany._get_field_types('res.company', target_conn)

        # Filtrer les champs simples
        simple_fields = [name for name, ttype in field_types.items() if ttype in ['char', 'integer', 'float', 'boolean']]

        # Préparer la liste des champs communs
        fields_to_sync = ', '.join(simple_fields)

        source_cursor = source_conn.cursor()
        target_cursor = target_conn.cursor()

        # Extraction des données dans la V16
        source_cursor.execute(f"""
            SELECT {fields_to_sync}
            FROM res_company
        """)
        companies = source_cursor.fetchall()
        _logger.info(f"{len(companies)} sociétés trouvées dans la base V16")

        for company in companies:
            company_data = dict(zip(simple_fields, company))

            # Vérification si la société existe dans la V18
            target_cursor.execute("""
                SELECT id FROM res_company WHERE id = %s
            """, (company_data['id'],))
            existing_company = target_cursor.fetchone()

            if existing_company:
                # Mise à jour dynamique
                set_clause = ', '.join([f"{col} = %s" for col in simple_fields if col != 'id'])
                values = [company_data[col] for col in simple_fields if col != 'id'] + [company_data['id']]
                _logger.info(f"Mise à jour de la société ID {company_data['id']}")
                target_cursor.execute(f"""
                    UPDATE res_company
                    SET {set_clause}
                    WHERE id = %s
                """, values)
            else:
                # Insertion dynamique
                columns_clause = ', '.join(simple_fields)
                placeholders = ', '.join(['%s'] * len(simple_fields))
                values = [company_data[col] for col in simple_fields]
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
