import flet as ft
from datetime import datetime
import os

class FournisseursView(ft.Container):
    """Vue Flet complète pour la gestion des fiches fournisseurs (CRUD) et de leurs documents (BC/BL)."""

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.expand = True
        self.padding = 15
        self.accent_color = self.app.entreprise.get("accent_color", "#2B719E")
        
        # Indexations et sélections
        self.documents = {}  # Index { (type, numero): doc_data }
        self.selected_doc_key = None  # Tuple (type_doc, num_doc)
        self.selected_fournisseur = None  # Dict du fournisseur sélectionné

        self._build_interface()
        self._refresh_fournisseurs_table()
        self._refresh_documents_table()

    def _build_interface(self):
        # --- EN-TÊTE PRINCIPAL ---
        header = ft.Row(
            controls=[
                ft.IconButton(ft.icons.ARROW_BACK_ROUNDED, on_click=lambda e: self.app.navigate_to("Dashboard")),
                ft.Text("🚚 Espace Fournisseurs & Logistique", size=24, weight=ft.FontWeight.BOLD),
            ],
            alignment=ft.MainAxisAlignment.START,
        )

        # ============================================================
        # ONGLET 1 : GESTION DES FICHES FOURNISSEURS
        # ============================================================
        
        # Barre d'outils fournisseurs
        fourn_toolbar = ft.Row(
            controls=[
                ft.ElevatedButton(
                    "➕ Ajouter un Fournisseur", 
                    bgcolor=self.accent_color, 
                    color=ft.colors.WHITE, 
                    icon=ft.icons.ADD_BUSINESS_ROUNDED,
                    on_click=lambda e: self.ouvrir_dialogue_fournisseur()
                ),
            ]
        )

        # Tableau des fournisseurs
        self.fourn_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Nom / Entreprise", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Téléphone", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Email", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("SIRET", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Adresse", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
            heading_row_color="#242426",
            show_checkbox_column=False,
        )

        fourn_table_container = ft.Container(
            content=ft.Column([ft.Row([self.fourn_table], scroll=ft.ScrollMode.AUTO)], scroll=ft.ScrollMode.AUTO, expand=True),
            bgcolor="#141416",
            border_radius=12,
            border=ft.border.all(1, "#2A2A2E"),
            padding=10,
            expand=True
        )

        fourn_actions = ft.Row(
            controls=[
                ft.ElevatedButton("✏️ Modifier la fiche", bgcolor="#F59E0B", color=ft.colors.WHITE, on_click=lambda e: self.modifier_fournisseur_selectionne()),
                ft.ElevatedButton("🗑️ Supprimer le fournisseur", bgcolor="#DC2626", color=ft.colors.WHITE, on_click=lambda e: self.supprimer_fournisseur_selectionne()),
            ],
            spacing=10
        )

        # 🔴 CORRECTION : Remplacement de tourn_table_container par fourn_table_container
        tab_fournisseurs_content = ft.Column(
            controls=[fourn_toolbar, fourn_table_container, fourn_actions],
            spacing=15,
            expand=True
        )

        # ============================================================
        # ONGLET 2 : GESTION DES DOCUMENTS (BC / BL)
        # ============================================================
        
        doc_toolbar = ft.Row(
            controls=[
                ft.ElevatedButton(
                    "➕ Nouveau Bon de Commande", 
                    bgcolor=self.accent_color, 
                    color=ft.colors.WHITE, 
                    on_click=lambda e: self.app.navigate_to("NouveauBonCommande")
                ),
                ft.ElevatedButton(
                    "➕ Nouveau Bon de Livraison", 
                    bgcolor=self.accent_color, 
                    color=ft.colors.WHITE, 
                    on_click=lambda e: self.app.navigate_to("NouveauBonLivraison")
                ),
            ],
            spacing=10
        )

        self.search_entry = ft.TextField(
            label="🔍 Filtrer les documents (Double-cliquez sur une ligne pour ouvrir le PDF)",
            bgcolor="#1A1A1C",
            height=45,
            text_size=13,
            on_change=self._refresh_documents_table,
            expand=True
        )

        self.doc_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Type", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Numéro", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Fournisseur", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Total TTC", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Statut", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
            heading_row_color="#242426",
            show_checkbox_column=False,
        )

        doc_table_container = ft.Container(
            content=ft.Column([ft.Row([self.doc_table], scroll=ft.ScrollMode.AUTO)], scroll=ft.ScrollMode.AUTO, expand=True),
            bgcolor="#141416",
            border_radius=12,
            border=ft.border.all(1, "#2A2A2E"),
            padding=10,
            expand=True
        )

        doc_actions = ft.Row(
            controls=[
                ft.ElevatedButton("👁️ Voir PDF", bgcolor="#2B719E", color=ft.colors.WHITE, on_click=self.ouvrir_pdf_selectionne),
                ft.ElevatedButton("💾 Exporter PDF Classé", bgcolor="#8B5CF6", color=ft.colors.WHITE, on_click=self.exporter_pdf_organise),
                ft.ElevatedButton("✏️ Modifier", bgcolor="#F59E0B", color=ft.colors.WHITE, on_click=self.modifier_doc_selectionne),
                ft.ElevatedButton("🔄 Convertir BC en BL", bgcolor="#0EA5E9", color=ft.colors.WHITE, on_click=self.convertir_bc_en_bl),
                ft.ElevatedButton("🗑️ Supprimer", bgcolor="#DC2626", color=ft.colors.WHITE, on_click=self.supprimer_doc_selectionne),
            ],
            spacing=8,
            wrap=True
        )

        tab_documents_content = ft.Column(
            controls=[doc_toolbar, ft.Row([self.search_entry]), doc_table_container, doc_actions],
            spacing=15,
            expand=True
        )

        # --- SYSTÈME D'ONGLETS CENTRALISÉ ---
        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(text="👥 Fiches Fournisseurs", content=tab_fournisseurs_content),
                ft.Tab(text="📄 Documents (BC & BL)", content=tab_documents_content),
            ],
            expand=True,
        )

        # Assemblage final
        self.content = ft.Column(
            controls=[header, self.tabs],
            spacing=15,
            expand=True
        )

    # ============================================================
    # LOGIQUE : GESTION DES FOURNISSEURS (CRUD)
    # ============================================================

    def _refresh_fournisseurs_table(self):
        self.fourn_table.rows.clear()
        self.selected_fournisseur = None
        
        fourn_list = getattr(self.app, "fournisseurs", [])
        
        for f in fourn_list:
            row = ft.DataRow(cells=[])
            
            def make_select_callback(fourn_dict, r_obj):
                return lambda e: self._select_fournisseur_row(fourn_dict, r_obj)
            
            row.cells = [
                ft.DataCell(ft.Text(f.get("nom", "Inconnu"), weight=ft.FontWeight.BOLD)),
                ft.DataCell(ft.Text(f.get("telephone", "-"))),
                ft.DataCell(ft.Text(f.get("email", "-"))),
                ft.DataCell(ft.Text(f.get("siret", "-"))),
                ft.DataCell(ft.Text(f.get("adresse", "-"))),
            ]
            row.on_select_changed = make_select_callback(f, row)
            self.fourn_table.rows.append(row)
            
        if self.page:
            self.page.update()

    def _select_fournisseur_row(self, fourn_dict, row_obj):
        for r in self.fourn_table.rows:
            r.selected = False
        row_obj.selected = True
        self.selected_fournisseur = fourn_dict
        self.page.update()

    def ouvrir_dialogue_fournisseur(self, fourn_to_edit=None):
        nom_tf = ft.TextField(label="Nom du Fournisseur / Entreprise", value=fourn_to_edit.get("nom", "") if fourn_to_edit else "")
        tel_tf = ft.TextField(label="Téléphone", value=fourn_to_edit.get("telephone", "") if fourn_to_edit else "")
        email_tf = ft.TextField(label="Email", value=fourn_to_edit.get("email", "") if fourn_to_edit else "")
        siret_tf = ft.TextField(label="Numéro SIRET", value=fourn_to_edit.get("siret", "") if fourn_to_edit else "")
        adresse_tf = ft.TextField(label="Adresse complète", multiline=True, min_lines=2, value=fourn_to_edit.get("adresse", "") if fourn_to_edit else "")

        def valider_enregistrement(e):
            if not nom_tf.value.strip():
                self.show_snack("Le nom du fournisseur est obligatoire.", is_error=True)
                return
            
            data = {
                "nom": nom_tf.value.strip(),
                "telephone": tel_tf.value.strip(),
                "email": email_tf.value.strip(),
                "siret": siret_tf.value.strip(),
                "adresse": adresse_tf.value.strip()
            }

            if fourn_to_edit:
                fourn_to_edit.update(data)
                self.show_snack("Fiche fournisseur mise à jour.")
            else:
                if not hasattr(self.app, "fournisseurs") or self.app.fournisseurs is None:
                    self.app.fournisseurs = []
                self.app.fournisseurs.append(data)
                self.show_snack("Nouveau fournisseur enregistré avec succès.")

            self.app.save_data()
            dialog.open = False
            self.page.update()
            self._refresh_fournisseurs_table()

        dialog = ft.AlertDialog(
            title=ft.Text("🏢 Fiche Fournisseur" if fourn_to_edit else "➕ Nouveau Fournisseur"),
            content=ft.Column([nom_tf, tel_tf, email_tf, siret_tf, adresse_tf], tight=True, spacing=10),
            actions=[
                ft.TextButton("Annuler", on_click=lambda _: setattr(dialog, "open", False) or self.page.update()),
                ft.ElevatedButton("Enregistrer", bgcolor=self.accent_color, color=ft.colors.WHITE, on_click=valider_enregistrement)
            ]
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def modifier_fournisseur_selectionne(self):
        if not self.selected_fournisseur:
            self.show_snack("Veuillez sélectionner un fournisseur à modifier.", is_error=True)
            return
        self.ouvrir_dialogue_fournisseur(self.selected_fournisseur)

    def supprimer_fournisseur_selectionne(self):
        if not self.selected_fournisseur:
            self.show_snack("Veuillez sélectionner un fournisseur à supprimer.", is_error=True)
            return

        def confirmer(confirme):
            dialog.open = False
            self.page.update()
            if confirme:
                self.app.fournisseurs.remove(self.selected_fournisseur)
                self.app.save_data()
                self._refresh_fournisseurs_table()
                self.show_snack("Fournisseur supprimé.")

        dialog = ft.AlertDialog(
            title=ft.Text("🚨 Suppression de compte"),
            content=ft.Text(f"Voulez-vous vraiment supprimer {self.selected_fournisseur.get('nom')} ?"),
            actions=[
                ft.TextButton("Annuler", on_click=lambda _: confirmer(False)),
                ft.TextButton("Supprimer", on_click=lambda _: confirmer(True), style=ft.ButtonStyle(color=ft.colors.RED_600))
            ]
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()


    # ============================================================
    # LOGIQUE : GESTION DES DOCUMENTS (BC / BL)
    # ============================================================

    def _refresh_documents_table(self, e=None):
        self.documents.clear()
        self.doc_table.rows.clear()
        self.selected_doc_key = None

        query = self.search_entry.value.strip().lower() if self.search_entry.value else ""

        bc_list = getattr(self.app, "bons_commande", [])
        bl_list = getattr(self.app, "bons_livraison", [])

        for bc in bc_list:
            if self._match_query(bc, "bon_commande", query):
                self._insert_document_row(bc, "bon_commande")
                
        for bl in bl_list:
            if self._match_query(bl, "bon_livraison", query):
                self._insert_document_row(bl, "bon_livraison")

        if self.page:
            self.page.update()

    def _match_query(self, doc, type_doc, query):
        if not query: return True
        num = str(doc.get("numero", "")).lower()
        fourn = doc.get("fournisseur", {})
        nom = fourn.get("nom", "").lower() if isinstance(fourn, dict) else str(fourn).lower()
        statut = str(doc.get("statut", "")).lower()
        readable_type = "bon de commande" if type_doc == "bon_commande" else "bon de livraison"
        return query in num or query in nom or query in statut or query in readable_type

    def _insert_document_row(self, doc, type_doc):
        num = str(doc.get("numero", ""))
        key = (type_doc, num)
        self.documents[key] = doc
        
        fourn = doc.get("fournisseur", {})
        nom = fourn.get("nom", "Inconnu") if isinstance(fourn, dict) else str(fourn)
        
        statut = doc.get("statut", "-")
        total_ttc = f"{float(doc.get('total_ttc', 0)):.2f} €"
        label_type = "BC" if type_doc == "bon_commande" else "BL"

        row = ft.DataRow(cells=[])

        def handle_single_tap(e):
            for r in self.doc_table.rows:
                r.selected = False
            row.selected = True
            self.selected_doc_key = key
            self.page.update()

        def handle_double_tap(e):
            handle_single_tap(e)
            self.exporter_pdf_direct(type_doc, doc, ouvrir_apres=True)

        def create_clickable_cell(text, color=None, weight=None):
            return ft.DataCell(
                ft.GestureDetector(
                    content=ft.Container(
                        content=ft.Text(text, color=color, weight=weight),
                        alignment=ft.alignment.center_left,
                        bgcolor=ft.colors.TRANSPARENT,
                        expand=True,
                    ),
                    on_tap=handle_single_tap,
                    on_double_tap=handle_double_tap,
                )
            )

        row.cells = [
            create_clickable_cell(label_type, weight=ft.FontWeight.BOLD, color="#8B5CF6" if label_type == "BC" else "#0EA5E9"),
            create_clickable_cell(num),
            create_clickable_cell(nom),
            create_clickable_cell(total_ttc, color=self.accent_color),
            create_clickable_cell(statut),
        ]
        
        self.doc_table.rows.append(row)

    def _selected_document(self):
        if not self.selected_doc_key:
            self.show_snack("Veuillez d'abord sélectionner un document dans le tableau.", is_error=True)
            return None, None
        type_doc, num_doc = self.selected_doc_key
        return type_doc, self.documents.get((type_doc, num_doc))

    def ouvrir_pdf_selectionne(self, e=None):
        type_doc, doc = self._selected_document()
        if doc: 
            self.exporter_pdf_direct(type_doc, doc, ouvrir_apres=True)

    def exporter_pdf_organise(self, e=None):
        type_doc, doc = self._selected_document()
        if doc: 
            self.exporter_pdf_direct(type_doc, doc, ouvrir_apres=False)

    def exporter_pdf_direct(self, type_doc, doc, ouvrir_apres=False):
        date_str = doc.get("date_creation", datetime.now().strftime("%d/%m/%Y"))
        try:
            parts = date_str.split("/")
            j, m, a = parts[0], parts[1], parts[2]
        except Exception:
            now = datetime.now()
            j, m, a = f"{now.day:02d}", f"{now.month:02d}", f"{now.year}"

        current_dir = os.path.dirname(os.path.abspath(__file__))
        if hasattr(self.app, "data_dir") and self.app.data_dir:
            base_dir = os.path.join(self.app.data_dir, "Documents_PDF")
        else:
            parent_dir = os.path.dirname(current_dir)
            base_dir = os.path.join(parent_dir, "data", "Documents_PDF")

        folder_path = os.path.join(base_dir, type_doc.capitalize(), a, m)
        
        try:
            os.makedirs(folder_path, exist_ok=True)
            file_name = f"{doc.get('numero', 'SANS_NUMERO')}.pdf"
            full_path = os.path.join(folder_path, file_name)
            
            self._generate_pdf_file(type_doc, doc, full_path)
            
            doc["pdf_path"] = full_path
            doc["pdf_to_load"] = full_path
            doc["type_doc_interne"] = type_doc
            
            if ouvrir_apres:
                self.app.current_doc = doc
                self.app.current_document = doc
                self.app.selected_document = doc
                self.app.navigate_to("PDFViewer")
            else:
                self.show_snack(f"⚡ PDF généré et classé sous : {full_path}")
                
        except Exception as ex:
            self.show_snack(f"Erreur d'exportation PDF : {ex}", is_error=True)

    def _generate_pdf_file(self, type_doc, doc, file_path):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
        except ImportError:
            raise ImportError("La bibliothèque 'reportlab' est absente.")

        doc_pdf = SimpleDocTemplate(file_path, pagesize=A4, rightMargin=35, leftMargin=35, topMargin=35, bottomMargin=35)
        story = []
        styles = getSampleStyleSheet()
        
        titre_propre = "BON DE COMMANDE" if type_doc == "bon_commande" else "BON DE LIVRAISON"
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor(self.accent_color),
            spaceAfter=15
        )
        normal = styles['Normal']
        
        num = doc.get("numero", "INCONNU")
        story.append(Paragraph(f"<b>{titre_propre} N° {num}</b>", title_style))
        story.append(Spacer(1, 10))

        date_crea = doc.get("date_creation", "-")
        f_info = doc.get("fournisseur", {})
        nom_f = f_info.get("nom", "Inconnu") if isinstance(f_info, dict) else str(f_info)
        
        meta_data = [
            [Paragraph(f"<b>Date :</b> {date_crea}", normal), Paragraph(f"<b>Fournisseur :</b> {nom_f}", normal)]
        ]
        t_meta = Table(meta_data, colWidths=[250, 250])
        t_meta.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
        story.append(t_meta)
        story.append(Spacer(1, 25))

        lines = doc.get("lignes", doc.get("articles", []))
        table_data = [["Désignation", "Qté", "Prix U. HT", "Total HT"]]
        
        for item in lines:
            des = item.get("designation", item.get("nom", "Article"))
            qte = str(item.get("quantite", item.get("qte", 1)))
            pu = f"{float(item.get('prix_unitaire', item.get('pu', 0))):.2f} €"
            tot = f"{float(item.get('total_ht', item.get('total_ht', 0))):.2f} €"
            table_data.append([des, qte, pu, tot])

        tot_ht = f"{float(doc.get('total_ht', 0)):.2f} €"
        tot_tva = f"{float(doc.get('tva', 0)):.2f} €"
        tot_ttc = f"{float(doc.get('total_ttc', 0)):.2f} €"
        
        table_data.append(["", "", "Total HT :", tot_ht])
        table_data.append(["", "", "TVA :", tot_tva])
        table_data.append(["", "", "Total TTC :", tot_ttc])

        t_lines = Table(table_data, colWidths=[240, 45, 115, 100])
        t_lines.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#242426")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,0), 'CENTER'),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('GRID', (0,0), (-1,-4), 0.5, colors.grey),
            ('LINEBELOW', (-2,-3), (-1,-1), 1, colors.HexColor(self.accent_color)),
            ('FONTNAME', (-2,-3), (-1,-1), 'Helvetica-Bold'),
            ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
        ]))
        story.append(t_lines)

        doc_pdf.build(story)

    def modifier_doc_selectionne(self, e=None):
        type_doc, doc = self._selected_document()
        if not doc: return
            
        from views.create_document import CreateDocumentView
        self.app.content_area.content = CreateDocumentView(app=self.app, doc_type=type_doc, doc_to_edit=doc)
        self.app.page.update()

    def supprimer_doc_selectionne(self, e=None):
        type_doc, doc = self._selected_document()
        if not doc: return

        def confirmation_action(confirme):
            dialog.open = False
            self.page.update()
            if confirme:
                if type_doc == "bon_commande": self.app.bons_commande.remove(doc)
                else: self.app.bons_livraison.remove(doc)
                self.app.save_data()
                self._refresh_documents_table()
                self.show_snack("Le document fournisseur a été supprimé.")

        dialog = ft.AlertDialog(
            title=ft.Text("🚨 Confirmation de suppression"),
            content=ft.Text(f"Supprimer définitivement le document n°{doc['numero']} ?"),
            actions=[
                ft.TextButton("Annuler", on_click=lambda _: confirmation_action(False)),
                ft.TextButton("Confirmer", on_click=lambda _: confirmation_action(True), style=ft.ButtonStyle(color=ft.colors.RED_600)),
            ]
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    def convertir_bc_en_bl(self, e=None):
        type_doc, doc = self._selected_document()
        if not doc: return
        
        if type_doc != "bon_commande":
            self.show_snack("Veuillez sélectionner un Bon de Commande.", is_error=True)
            return

        bl_list = getattr(self.app, "bons_livraison", [])
        num_bl = f"BL-{datetime.now().year}-{len(bl_list) + 1:03d}"

        nouveau_bl = {
            "numero": num_bl,
            "fournisseur": doc.get("fournisseur"),
            "articles": list(doc.get("articles", [])),
            "lignes": list(doc.get("lignes", doc.get("articles", []))),
            "total_ht": doc.get("total_ht", 0),
            "tva": doc.get("tva", 0),
            "total_ttc": doc.get("total_ttc", 0),
            "date_creation": datetime.now().strftime("%d/%m/%Y"),
            "statut": "Reçu",
        }

        self.app.bons_livraison.append(nouveau_bl)
        doc["statut"] = "Livré"
        self.app.save_data()
        self._refresh_documents_table()
        self.show_snack(f"Bon de Livraison {num_bl} généré ! 🔄")

    def show_snack(self, message, is_error=False):
        self.app.page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.colors.RED_700 if is_error else ft.colors.GREEN_700
        )
        self.app.page.snack_bar.open = True
        self.app.page.update()