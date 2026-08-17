import flet as ft
from datetime import datetime, timedelta
import random
import re

class CreateDocumentView(ft.Container):
    """
    Vue professionnelle et centralisée pour la création et la modification de tous les documents 
    de l'application (Devis, Factures, Bons de commande, Bons de livraison).
    Gère dynamiquement le flux Client ou Fournisseur en totale conformité légale.
    """
    def __init__(self, app, doc_type="devis", doc_to_edit=None):
        super().__init__()
        self.app = app
        self.doc_type = doc_type  # "devis", "facture", "bon_commande", "bon_livraison"
        self.doc_to_edit = doc_to_edit  # Contient le dictionnaire du document si mode édition
        self.expand = True
        self.padding = 20

        # 🎨 Configuration de la couleur d'accentuation de l'entreprise
        self.accent_color = "#2B719E"
        if hasattr(self.app, "entreprise") and isinstance(self.app.entreprise, dict):
            self.accent_color = self.app.entreprise.get("accent_color", "#2B719E")

        # 🛡️ CONFIGURATION DYNAMIQUE DU FLUX (Clients vs Fournisseurs)
        if self.doc_type in ["bon_commande", "bon_livraison"]:
            self.tiers_list = getattr(app, "fournisseurs", []) or []
            self.tiers_label = "Fournisseur (Sélection)"
            self.fallback_msg = "Aucun fournisseur enregistré"
            self.redirect_view = "Fournisseurs"
        else:
            self.tiers_list = getattr(app, "clients", []) or []
            self.tiers_label = "Client (Sélection)"
            self.fallback_msg = "Aucun client enregistré"
            self.redirect_view = "Facturation"

        self.articles_catalogue = getattr(app, "articles", []) or []
        self.entreprise = getattr(app, "entreprise", {}) or {}

        # Récupération défensive des lignes existantes en cas de modification
        self.current_lines = []
        if self.doc_to_edit:
            lignes_existantes = self.doc_to_edit.get("lignes", self.doc_to_edit.get("articles", []))
            for lg in lignes_existantes:
                pu = float(lg.get("pu", lg.get("prix", lg.get("prix_unitaire", 0))))
                qty = int(lg.get("qty", lg.get("qte", lg.get("quantite", 1))))
                self.current_lines.append({
                    "designation": lg.get("designation", lg.get("nom", "Article")),
                    "pu": pu,
                    "qty": qty,
                    "total_ht": pu * qty
                })

        self.setup_ui()

    def setup_ui(self):
        # 1. En-tête avec titre dynamique
        if self.doc_to_edit:
            titre = f"✏️ Modifier le Document {self.doc_to_edit.get('numero')}"
        else:
            titre_map = {
                "devis": "📄 Nouveau Devis Client",
                "facture": "💰 Nouvelle Facture Client",
                "bon_commande": "🛒 Nouveau Bon de Commande Fournisseur",
                "bon_livraison": "📦 Nouveau Bon de Livraison Fournisseur"
            }
            titre = titre_map.get(self.doc_type, "📄 Nouveau Document")
            
        header = ft.Row(
            controls=[
                ft.IconButton(
                    icon=ft.icons.ARROW_BACK_ROUNDED, 
                    icon_color=ft.colors.WHITE,
                    on_click=lambda e: self.app.navigate_to(self.redirect_view)
                ),
                ft.Text(titre, size=22, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE),
            ],
            alignment=ft.MainAxisAlignment.START,
        )

        scroll_content = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=20)

        # Bandeau visuel si c'est une facture déjà payée
        if self.doc_to_edit and self.doc_to_edit.get("statut") == "Payée":
            date_p = self.doc_to_edit.get("date_paiement", "Inconnue")
            stamp_container = ft.Container(
                content=ft.Text(f"✅ FACTURE PAYÉE LE {date_p} ◆ ENCAISSEMENT COMPTABILISÉ", size=13, weight=ft.FontWeight.BOLD, color="#10B981"),
                bgcolor="#142E24",
                border=ft.border.all(1.5, "#10B981"),
                border_radius=8,
                padding=12,
                alignment=ft.alignment.center
            )
            scroll_content.controls.append(stamp_container)

        # =====================================================================
        # SECTION 1 : INFORMATIONS GÉNÉRALES ET RÉGLEMENTAIRES (BLOC CARD)
        # =====================================================================
        tiers_options = [ft.dropdown.Option(t.get("nom", "Inconnu")) for t in self.tiers_list]
        if not tiers_options:
            tiers_options = [ft.dropdown.Option(self.fallback_msg)]

        self.client_dropdown = ft.Dropdown(
            label=self.tiers_label,
            options=tiers_options,
            bgcolor="#1E1E22",
            border_color="#2A2A2E",
            border_radius=6,
            expand=2
        )
        
        if self.doc_to_edit:
            t_info = self.doc_to_edit.get("fournisseur", self.doc_to_edit.get("client", self.doc_to_edit.get("fournisseur_nom", "")))
            self.client_dropdown.value = t_info.get("nom", "") if isinstance(t_info, dict) else str(t_info)
        else:
            if self.tiers_list:
                self.client_dropdown.value = self.tiers_list[0].get("nom", "")
            else:
                self.client_dropdown.value = self.fallback_msg

        date_initiale = self.doc_to_edit.get("date_creation", datetime.now().strftime("%d/%m/%Y")) if self.doc_to_edit else datetime.now().strftime("%d/%m/%Y")
        self.date_field = ft.TextField(
            label="Date d'émission",
            value=date_initiale,
            bgcolor="#1E1E22",
            border_color="#2A2A2E",
            border_radius=6,
            expand=1
        )

        # Label dynamique selon le type de pièce pour rester conforme à la législation
        label_echeance = "Date limite de livraison" if self.doc_type in ["bon_commande", "bon_livraison"] else "Date d'échéance règlement"
        date_ech_init = self.doc_to_edit.get("date_echeance", (datetime.now() + timedelta(days=30)).strftime("%d/%m/%Y")) if self.doc_to_edit else (datetime.now() + timedelta(days=30)).strftime("%d/%m/%Y")
        self.date_echeance_field = ft.TextField(
            label=label_echeance,
            value=date_ech_init,
            bgcolor="#1E1E22",
            border_color="#2A2A2E",
            border_radius=6,
            expand=1
        )

        self.mode_reglement = ft.Dropdown(
            label="Mode de règlement requis",
            options=[
                ft.dropdown.Option("Virement Bancaire"),
                ft.dropdown.Option("Carte Bancaire"),
                ft.dropdown.Option("Chèque"),
                ft.dropdown.Option("Espèces"),
                ft.dropdown.Option("Prélèvement auto")
            ],
            value=self.doc_to_edit.get("mode_reglement", "Virement Bancaire") if self.doc_to_edit else "Virement Bancaire",
            bgcolor="#1E1E22",
            border_color="#2A2A2E",
            border_radius=6,
            expand=1
        )

        self.regime_tva = ft.Dropdown(
            label="Régime de TVA légal",
            options=[
                ft.dropdown.Option("TVA Standard (20%)"),
                ft.dropdown.Option("TVA Réduite (10%)"),
                ft.dropdown.Option("TVA Particulière (5.5%)"),
                ft.dropdown.Option("Exonéré (Art. 293 B du CGI)")
            ],
            value="Exonéré (Art. 293 B du CGI)" if self.entreprise.get("soumis_tva", "Non") == "Non" else "TVA Standard (20%)",
            bgcolor="#1E1E22",
            border_color="#2A2A2E",
            border_radius=6,
            expand=1,
            on_change=lambda e: self.refresh_tree()
        )

        info_block = ft.Container(
            content=ft.Column([
                ft.Text("📋 CONFIGURATION ET INFORMATIONS LÉGALES", size=12, weight=ft.FontWeight.BOLD, color=self.accent_color),
                ft.Row(controls=[self.client_dropdown, self.date_field, self.date_echeance_field], spacing=12),
                ft.Row(controls=[self.mode_reglement, self.regime_tva], spacing=12)
            ], spacing=12),
            bgcolor="#141416",
            border=ft.border.all(1, "#2A2A2E"),
            padding=15,
            border_radius=8
        )
        scroll_content.controls.append(info_block)

        # =====================================================================
        # SECTION 2 : SAISIE DE LIGNE (CATALOGUE / LIBRE)
        # =====================================================================
        article_options = [ft.dropdown.Option(a.get("designation", "")) for a in self.articles_catalogue]
        if not article_options:
            article_options = [ft.dropdown.Option("Aucun article disponible")]

        self.article_dropdown = ft.Dropdown(
            label="Rechercher dans le catalogue",
            options=article_options,
            bgcolor="#1E1E22",
            border_color="#2A2A2E",
            border_radius=6,
            on_change=self.on_article_select,
            width=250
        )

        self.designation_field = ft.TextField(
            label="Désignation de la prestation ou de l'article (Saisie libre autorisée)",
            bgcolor="#1E1E22",
            border_color="#2A2A2E",
            border_radius=6,
            expand=True
        )

        self.pu_field = ft.TextField(
            label="P.U. HT (€)",
            bgcolor="#1E1E22",
            border_color="#2A2A2E",
            border_radius=6,
            width=130
        )

        self.qty_field = ft.TextField(
            label="Qté",
            value="1",
            bgcolor="#1E1E22",
            border_color="#2A2A2E",
            border_radius=6,
            width=80
        )

        btn_add = ft.ElevatedButton(
            text="➕ Insérer la ligne",
            bgcolor=ft.colors.GREEN_700,
            color=ft.colors.WHITE,
            height=48,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
            on_click=self.add_line
        )

        add_block = ft.Container(
            content=ft.Column([
                ft.Text("🛒 LIGNE DE PRESTATION / MARCHANDISE", size=12, weight=ft.FontWeight.BOLD, color=self.accent_color),
                ft.Row(controls=[self.article_dropdown, self.designation_field], spacing=10),
                ft.Row(controls=[self.pu_field, self.qty_field, btn_add], spacing=10, alignment=ft.MainAxisAlignment.END)
            ], spacing=12),
            bgcolor="#141416",
            border=ft.border.all(1, "#2A2A2E"),
            padding=15,
            border_radius=8
        )
        scroll_content.controls.append(add_block)

        # =====================================================================
        # SECTION 3 : TABLEAU RÉCAPITULATIF DES LIGNES
        # =====================================================================
        self.table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Désignation des lignes", weight=ft.FontWeight.BOLD, color=ft.colors.GREY_300)),
                ft.DataColumn(ft.Text("P.U. HT", weight=ft.FontWeight.BOLD, color=ft.colors.GREY_300)),
                ft.DataColumn(ft.Text("Quantité", weight=ft.FontWeight.BOLD, color=ft.colors.GREY_300)),
                ft.DataColumn(ft.Text("Total HT", weight=ft.FontWeight.BOLD, color=ft.colors.GREY_300)),
                ft.DataColumn(ft.Text("Action", weight=ft.FontWeight.BOLD, color=ft.colors.GREY_300)),
            ],
            rows=[],
            heading_row_color="#1E1E22",
            show_checkbox_column=False,
        )

        table_container = ft.Container(
            content=ft.Column(
                controls=[ft.Row(controls=[self.table], scroll=ft.ScrollMode.AUTO)],
                scroll=ft.ScrollMode.AUTO
            ),
            bgcolor="#141416",
            border_radius=8,
            border=ft.border.all(1, "#2A2A2E"),
            padding=10,
            height=280
        )
        scroll_content.controls.append(table_container)

        # =====================================================================
        # SECTION 4 : OBSERVATIONS, TOTAUX ET VALIDATION
        # =====================================================================
        self.notes_field = ft.TextField(
            label="Observations / Conditions Particulières / Mentions légales complémentaires",
            value=self.doc_to_edit.get("notes", "") if self.doc_to_edit else "",
            multiline=True,
            min_lines=3,
            max_lines=3,
            bgcolor="#1E1E22",
            border_color="#2A2A2E",
            border_radius=6,
            expand=True
        )

        self.lbl_total_ht = ft.Text("Total Global HT : 0.00 €", size=13, weight=ft.FontWeight.W_500)
        self.lbl_tva = ft.Text("TVA (20%) : 0.00 €", size=13, visible=True)
        self.lbl_total_ttc = ft.Text("NET À PAYER : 0.00 €", size=16, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_400)

        totals_frame = ft.Container(
            content=ft.Column(
                controls=[self.lbl_total_ht, self.lbl_tva, self.lbl_total_ttc],
                horizontal_alignment=ft.CrossAxisAlignment.END,
                spacing=6
            ),
            bgcolor="#1E1E22",
            padding=15,
            border_radius=8,
            width=280,
            border=ft.border.all(1, "#2A2A2E")
        )

        bottom_row = ft.Row(
            controls=[self.notes_field, totals_frame],
            spacing=15,
            vertical_alignment=ft.CrossAxisAlignment.START
        )
        scroll_content.controls.append(bottom_row)

        # Boutons d'actions d'enregistrement
        texte_bouton = "💾 Appliquer et Enregistrer les modifications" if self.doc_to_edit else "💾 Valider et Générer le Document"
        btn_save = ft.ElevatedButton(
            text=texte_bouton,
            height=46,
            bgcolor=self.accent_color,
            color=ft.colors.WHITE,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
            on_click=self.save_document,
            expand=True
        )

        btn_cancel = ft.ElevatedButton(
            text="🔄 Annuler",
            height=46,
            bgcolor="#3A3A3C",
            color=ft.colors.WHITE,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
            on_click=lambda e: self.app.navigate_to(self.redirect_view)
        )

        footer_row = ft.Row(controls=[btn_cancel, btn_save], spacing=12)
        scroll_content.controls.append(footer_row)

        self.content = ft.Column(
            controls=[header, scroll_content],
            spacing=15,
            expand=True
        )

        self.refresh_tree()

    def on_article_select(self, e):
        choice = self.article_dropdown.value
        if choice == "Aucun article disponible" or not choice: return
        for art in self.articles_catalogue:
            if art.get("designation") == choice:
                self.designation_field.value = choice
                prix = art.get('prix_ht', art.get('pu', 0))
                self.pu_field.value = f"{float(prix):.2f}"
                self.page.update()
                break

    def add_line(self, e):
        desc = self.designation_field.value or ""
        desc = desc.strip()
        if not desc:
            self.show_snack("Veuillez indiquer une désignation pour le produit.", is_error=True)
            return

        raw_pu = self.pu_field.value or "0"
        raw_qty = self.qty_field.value or "1"

        try:
            pu = float(raw_pu.replace(",", "."))
            qty = int(raw_qty)
        except (ValueError, AttributeError):
            self.show_snack("Prix unitaire ou quantité invalide.", is_error=True)
            return
            
        total_ht = pu * qty
        line_data = {"designation": desc, "pu": pu, "qty": qty, "total_ht": total_ht}
        
        self.current_lines.append(line_data)
        self.refresh_tree()
        
        article_existe = any(a.get("designation", "").lower() == desc.lower() for a in self.articles_catalogue)
        if not article_existe:
            ref_auto = f"ART-{datetime.now().strftime('%M%S')}{random.randint(10,99)}"
            taux_tva = 20.0 if "20%" in str(self.regime_tva.value) else 0.0
            nouvel_article = {
                "ref": ref_auto, "designation": desc, "categorie": "Créé à la volée",
                "prix_ht": pu, "tva": taux_tva, "stock": 0
            }
            self.articles_catalogue.append(nouvel_article)
            if hasattr(self.app, "save_data"): self.app.save_data()
            self.article_dropdown.options = [ft.dropdown.Option(a.get("designation", "")) for a in self.articles_catalogue]

        self.article_dropdown.value = ""
        self.designation_field.value = ""
        self.pu_field.value = ""
        self.qty_field.value = "1"
        self.page.update()

    def delete_selected_line(self, index):
        self.current_lines.pop(index)
        self.refresh_tree()
        self.page.update()

    def refresh_tree(self):
        self.table.rows.clear()
        total_ht_global = 0.0
        
        for i, line in enumerate(self.current_lines):
            total_ht_global += line["total_ht"]
            self.table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(line["designation"], color=ft.colors.WHITE)),
                        ft.DataCell(ft.Text(f"{line['pu']:.2f} €", color=ft.colors.WHITE)),
                        ft.DataCell(ft.Text(str(line["qty"]), color=ft.colors.WHITE)),
                        ft.DataCell(ft.Text(f"{line['total_ht']:.2f} €", color=ft.colors.WHITE)),
                        ft.DataCell(
                            ft.IconButton(
                                icon=ft.icons.DELETE_ROUNDED,
                                icon_color=ft.colors.RED_400,
                                on_click=lambda e, idx=i: self.delete_selected_line(idx)
                            )
                        ),
                    ]
                )
            )

        self.lbl_total_ht.value = f"Total Global HT : {total_ht_global:.2f} €"
        
        # Calcul de TVA basé sur la conformité du dropdown légal sélectionné
        regime = str(self.regime_tva.value)
        if "20%" in regime:
            taux = 0.20
            self.lbl_tva.value = f"TVA (20%) : {total_ht_global * taux:.2f} €"
            self.lbl_tva.visible = True
        elif "10%" in regime:
            taux = 0.10
            self.lbl_tva.value = f"TVA (10%) : {total_ht_global * taux:.2f} €"
            self.lbl_tva.visible = True
        elif "5.5%" in regime:
            taux = 0.055
            self.lbl_tva.value = f"TVA (5.5%) : {total_ht_global * taux:.2f} €"
            self.lbl_tva.visible = True
        else:
            taux = 0.0
            self.lbl_tva.value = "TVA (0%) : 0.00 €"
            self.lbl_tva.visible = False
            
        tva_calculee = total_ht_global * taux
        total_ttc = total_ht_global + tva_calculee
            
        self.lbl_total_ttc.value = f"NET À PAYER : {total_ttc:.2f} €" if self.doc_type not in ["bon_livraison"] else f"TOTAL ESTIMÉ : {total_ttc:.2f} €"
        if self.page:
            self.page.update()

    def _generate_auto_increment_number(self):
        prefix_cle = f"prefix_{self.doc_type}"
        fallback_prefixes = {
            "devis": f"DEV-{datetime.now().year}-",
            "facture": f"FACT-{datetime.now().year}-",
            "bon_commande": f"BC-{datetime.now().year}-",
            "bon_livraison": f"BL-{datetime.now().year}-"
        }
        prefix = self.entreprise.get(prefix_cle, fallback_prefixes.get(self.doc_type, "DOC-"))
        
        liste_cible_map = {
            "devis": "devis",
            "facture": "factures",
            "bon_commande": "bons_commande",
            "bon_livraison": "bons_livraison"
        }
        liste_cible = getattr(self.app, liste_cible_map.get(self.doc_type, "devis"), [])
        maxi = 0
        for doc in liste_cible:
            m = re.search(r"(\d+)$", str(doc.get("numero", "")))
            if m: maxi = max(maxi, int(m.group(1)))
                
        return f"{prefix}{maxi + 1:03d}"

    def save_document(self, e):
        client_selected = self.client_dropdown.value
        if not client_selected or client_selected in ["Aucun client enregistré", "Aucun fournisseur enregistré"]:
            self.show_snack(f"Veuillez sélectionner un tiers valide.", is_error=True)
            return
        if not self.current_lines:
            self.show_snack("Votre document doit contenir au moins une ligne de commande.", is_error=True)
            return

        # Identification de l'objet dictionnaire complet du client ou fournisseur
        matched_tiers = next((t for t in self.tiers_list if t.get("nom") == client_selected), {"nom": client_selected})

        total_ht = sum(l["total_ht"] for l in self.current_lines)
        regime = str(self.regime_tva.value)
        taux = 0.20 if "20%" in regime else (0.10 if "10%" in regime else (0.055 if "5.5%" in regime else 0.0))
        tva = total_ht * taux
        total_ttc = total_ht + tva

        liste_cible_map = {
            "devis": "devis",
            "facture": "factures",
            "bon_commande": "bons_commande",
            "bon_livraison": "bons_livraison"
        }
        liste_cible = getattr(self.app, liste_cible_map.get(self.doc_type, "devis"), [])

        if self.doc_to_edit:
            num_doc = self.doc_to_edit.get("numero")
            doc_data = self.doc_to_edit
        else:
            num_doc = self._generate_auto_increment_number()
            doc_data = {}
            liste_cible.append(doc_data)

        # Construction sécurisée conforme à la structure de données attendue
        doc_data.update({
            "numero": num_doc,
            "date_creation": self.date_field.value,
            "date_echeance": self.date_echeance_field.value,
            "mode_reglement": self.mode_reglement.value,
            "regime_tva": regime,
            "statut": doc_data.get("statut", "Brouillon" if self.doc_type in ["devis", "facture", "bon_commande"] else "Reçu"),
            "articles": self.current_lines,
            "lignes": self.current_lines,
            "total_ht": total_ht,
            "montant_ht": total_ht,
            "tva": tva,
            "montant_tva": tva,
            "total_ttc": total_ttc,
            "montant_ttc": total_ttc,
            "notes": self.notes_field.value,
            "type_doc_interne": self.doc_type
        })

        # Affectation propre de l'objet Tiers selon le flux (Évite les mélanges et les bugs de rendu)
        if self.doc_type in ["bon_commande", "bon_livraison"]:
            doc_data["fournisseur"] = matched_tiers
            doc_data["client"] = None
        else:
            doc_data["client"] = matched_tiers
            doc_data["fournisseur"] = None

        if hasattr(self.app, "save_data"): self.app.save_data()
        self.show_snack(f"Le document {num_doc} a été sauvegardé avec succès.")
        self.app.navigate_to(self.redirect_view)

    def show_snack(self, message, is_error=False):
        self.app.page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.colors.RED_700 if is_error else ft.colors.GREEN_700
        )
        self.app.page.snack_bar.open = True
        self.app.page.update()