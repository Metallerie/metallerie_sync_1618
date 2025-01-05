class SyncFieldStatus(models.Model):
    _name = 'metallerie.sync.field_status'
    _description = 'Statut de synchronisation des champs'

    field_name = fields.Char(string="Nom du champ")
    field_type = fields.Char(string="Type du champ")
    field_relation = fields.Char(string="Relation")
    field_status = fields.Selection([('synced', 'Synchronisé'), ('ignored', 'Ignoré')], string="Statut")
    ignore_reason = fields.Text(string="Raison ignorée")

