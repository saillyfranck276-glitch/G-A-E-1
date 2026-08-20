import csv
from datetime import datetime
import re
import flet as ft


def safe_border(width=1, color="#424242"):
    """Bordure universelle sécurisée."""
    side = ft.BorderSide(width, color)
    return ft.Border(top=side, right=side, bottom=side, left=side)


def extract_client_name(client_data):
    """Extrait proprement le nom du client s'il s'agit d'un dictionnaire ou d'une chaîne."""
    if isinstance(client_data, dict):
        return (
            client_data.get("nom")
            or client_data.get("contact_nom")
            or client_data.get("entreprise")
            or "Inconnu"
        )
    if isinstance(client_data, str) and client_data.strip():
        return client_data.strip()
    return "Inconnu"


class FacturationView(ft.Container):
    """Vue Flet complète pour la gestion des devis et factures."""

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.expand = True
        self.padding = 10

        self.accent_color = (
            getattr(self.app, "entreprise", {}).get("accent_color")
            if hasattr(self.app, "entreprise")
            else "#2B719E"
        )
        self.documents = {}  # Index { (type_doc, numero): doc_data }
        self.selected_key = None  # (type_doc, numero)

        self.file_picker = ft.FilePicker(on_result=self._on_csv_picked)

        self.display_container = ft.Container(expand=True)
        self.main_layout = ft.Column(spacing=10, expand=True)
        self.content = self.main_layout
        self._build_interface()

    def safe_update(self):
        """Met à jour le composant uniquement s'il est rattaché à la page."""
        if self.page:
            try:
                self.update()
            except Exception:
                pass

    def did_mount(self):
        """Déclenché quand le contrôle est rattaché à la page."""
        if self.page and self.file_picker not in self.page.overlay:
            self.page.overlay.append(self.file_picker)

        if hasattr(self.app, "load_data"):
            self.app.load_data()
        self._refresh_table()

    def _is_mobile(self):
        return self.page.width < 768 if (self.page and self.page.width) else False

    def _build_interface(self):
        # 1. EN-TÊTE ET BARRE D'OUTILS PRINCIPALE
        header = ft.Row(
            controls=[
                ft.IconButton(
                    icon="arrow_back",
                    icon_color="white",
                    tooltip="Retour",
                    on_click=lambda e: self.app.navigate_to("Dashboard"),
                ),
                ft.Text("📂 Gestion des Documents", size=22, weight=ft.FontWeight.BOLD, color="white"),
            ]
        )

        button_style = ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))

        top_buttons = ft.Row(
            controls=[
                ft.ElevatedButton(
                    "➕ Nouveau Devis",
                    bgcolor=self.accent_color,
                    color="white",
                    height=38,
                    style=button_style,
                    on_click=lambda e: self._creer_document("devis"),
                ),
                ft.ElevatedButton(
                    "➕ Nouvelle Facture",
                    bgcolor=self.accent_color,
                    color="white",
                    height=38,
                    style=button_style,
                    on_click=lambda e: self._creer_document("facture"),
                ),
            ],
            spacing=10,
        )

        # 2. BARRE DE RECHERCHE DYNAMIQUE
        self.search_entry = ft.TextField(
            hint_text="🔍 Rechercher par numéro, client, statut...",
            bgcolor="#1A1A1C",
            height=42,
            text_size=13,
            content_padding=10,
            border_color="#2A2A32",
            focused_border_color=self.accent_color,
            text_style=ft.TextStyle(color="white"),
            on_change=self._refresh_table,
        )

        # 3. TABLEAU D'AFFICHAGE (DESKTOP)
        self.table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Type", weight=ft.FontWeight.BOLD, color="white")),
                ft.DataColumn(ft.Text("Numéro", weight=ft.FontWeight.BOLD, color="white")),
                ft.DataColumn(ft.Text("Client", weight=ft.FontWeight.BOLD, color="white")),
                ft.DataColumn(ft.Text("Total TTC", weight=ft.FontWeight.BOLD, color="white")),
                ft.DataColumn(ft.Text("Statut", weight=ft.FontWeight.BOLD, color="white")),
                ft.DataColumn(ft.Text("URSSAF", weight=ft.FontWeight.BOLD, color="white")),
            ],
            rows=[],
            heading_row_color="#242426",
            show_checkbox_column=False,
            expand=True,
        )

        # 4. ZONE DES ACTIONS INTERACTIVES
        actions = ft.ResponsiveRow(
            controls=[
                ft.Column(
                    [
                        ft.ElevatedButton(
                            "✏️ Modifier",
                            bgcolor="#F59E0B",
                            color="white",
                            height=38,
                            style=button_style,
                            on_click=self.modifier_selectionne,
                        )
                    ],
                    col={"xs": 6, "sm": 2},
                ),
                ft.Column(
                    [
                        ft.ElevatedButton(
                            "💶 Marquer Payée",
                            bgcolor="#10B981",
                            color="white",
                            height=38,
                            style=button_style,
                            on_click=self.marquer_payee,
                        )
                    ],
                    col={"xs": 6, "sm": 2},
                ),
                ft.Column(
                    [
                        ft.ElevatedButton(
                            "✅ Déclarer URSSAF",
                            bgcolor="#16A34A",
                            color="white",
                            height=38,
                            style=button_style,
                            on_click=self.declarer_urssaf,
                        )
                    ],
                    col={"xs": 6, "sm": 2},
                ),
                ft.Column(
                    [
                        ft.ElevatedButton(
                            "🔄 Convertir",
                            bgcolor="#0EA5E9",
                            color="white",
                            height=38,
                            style=button_style,
                            on_click=self.convertir_devis_en_facture,
                        )
                    ],
                    col={"xs": 6, "sm": 2},
                ),
                ft.Column(
                    [
                        ft.ElevatedButton(
                            "📊 Exporter CSV",
                            bgcolor="#4F46E5",
                            color="white",
                            height=38,
                            style=button_style,
                            on_click=self.exporter_csv,
                        )
                    ],
                    col={"xs": 6, "sm": 2},
                ),
                ft.Column(
                    [
                        ft.ElevatedButton(
                            "🗑️ Supprimer",
                            bgcolor="#DC2626",
                            color="white",
                            height=38,
                            style=button_style,
                            on_click=self.supprimer_selectionne,
                        )
                    ],
                    col={"xs": 6, "sm": 2},
                ),
            ],
            spacing=8,
        )

        self.main_layout.controls = [
            header,
            top_buttons,
            self.search_entry,
            self.display_container,
            actions,
        ]

    # =========================================================================
    # LOGIQUE RAFRAÎCHISSEMENT ET FILTRAGE
    # =========================================================================
    def _refresh_table(self, e=None):
        if hasattr(self.app, "load_data"):
            self.app.load_data()

        self.documents.clear()
        query = (
            self.search_entry.value.strip().lower()
            if self.search_entry and self.search_entry.value
            else ""
        )

        filtered_docs = []

        # Parcours Devis
        for devis in getattr(self.app, "devis", []):
            if self._match_query(devis, "devis", query):
                num = str(devis.get("numero", ""))
                self.documents[("devis", num)] = devis
                filtered_docs.append(("devis", num, devis))

        # Parcours Factures
        for facture in getattr(self.app, "factures", []):
            if self._match_query(facture, "facture", query):
                num = str(facture.get("numero", ""))
                self.documents[("facture", num)] = facture
                filtered_docs.append(("facture", num, facture))

        if self._is_mobile():
            self._render_mobile(filtered_docs)
        else:
            self._render_desktop(filtered_docs)

        self.safe_update()

    def _match_query(self, doc, type_doc, query):
        if not query:
            return True
        num = str(doc.get("numero", "")).lower()
        client_nom = extract_client_name(doc.get("client", {})).lower()
        statut = str(doc.get("statut", "")).lower()
        return query in num or query in client_nom or query in statut or query in type_doc

    # =========================================================================
    # RENDU DEKSTOP ET MOBILE
    # =========================================================================
    def _render_desktop(self, filtered_docs):
        self.table.rows.clear()
        for type_doc, num, doc in filtered_docs:
            key = (type_doc, num)
            is_selected = self.selected_key == key

            row = ft.DataRow(cells=[], selected=is_selected)

            def make_select_handler(k):
                return lambda e: self._select_document(k)

            def make_double_click_handler(d):
                return lambda e: self.ouvrir_pdf(d)

            nom = extract_client_name(doc.get("client", {}))
            montant = float(doc.get("total_ttc", doc.get("montant_ttc", 0)))

            statut = doc.get("statut", "-")
            if statut == "Payée" and doc.get("date_paiement"):
                statut = f"Payée ({doc.get('date_paiement')})"

            urssaf_txt = "Oui" if doc.get("urssaf_declare") else "Non"

            row.cells = [
                ft.DataCell(ft.Text(type_doc.capitalize(), color="white"), on_tap=make_select_handler(key)),
                ft.DataCell(
                    ft.Text(str(num), color="white", weight=ft.FontWeight.BOLD),
                    on_tap=make_select_handler(key),
                    on_double_tap=make_double_click_handler(doc),
                ),
                ft.DataCell(ft.Text(nom, color="white"), on_tap=make_select_handler(key)),
                ft.DataCell(ft.Text(f"{montant:.2f} €", color="white"), on_tap=make_select_handler(key)),
                ft.DataCell(
                    ft.Text(
                        str(statut),
                        color="#34D399" if "payée" in str(statut).lower() or "déclarée" in str(statut).lower() else "#FBBF24",
                    ),
                    on_tap=make_select_handler(key),
                ),
                ft.DataCell(ft.Text(urssaf_txt, color="white"), on_tap=make_select_handler(key)),
            ]

            self.table.rows.append(row)

        self.display_container.content = ft.Container(
            content=ft.Column([self.table], scroll=ft.ScrollMode.AUTO, expand=True),
            bgcolor="#141416",
            border_radius=10,
            border=safe_border(1, "#2A2A2E"),
            padding=8,
            expand=True,
        )

    def _render_mobile(self, filtered_docs):
        cards = []
        for type_doc, num, doc in filtered_docs:
            key = (type_doc, num)
            is_selected = self.selected_key == key

            nom = extract_client_name(doc.get("client", {}))
            montant = float(doc.get("total_ttc", doc.get("montant_ttc", 0)))
            statut = doc.get("statut", "-")

            def make_select_handler(k):
                return lambda e: self._select_document(k)

            cards.append(
                ft.Container(
                    bgcolor="#2A3A4E" if is_selected else "#1E1E22",
                    border=safe_border(1.5 if is_selected else 1, self.accent_color if is_selected else "#2A2A32"),
                    border_radius=10,
                    padding=12,
                    on_click=make_select_handler(key),
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(f"[{type_doc.upper()}] {num}", weight=ft.FontWeight.BOLD, color="white"),
                                    ft.Text(f"{montant:.2f} €", color="#10B981", weight=ft.FontWeight.BOLD),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Text(f"Client : {nom}", color="white", size=12),
                            ft.Text(f"Statut : {statut}", size=11, color="#AEAEB2"),
                        ],
                        spacing=4,
                    ),
                )
            )

        self.display_container.content = ft.ListView(controls=cards, spacing=8, expand=True)

    def _select_document(self, key):
        if self.selected_key == key:
            self.selected_key = None
        else:
            self.selected_key = key
        self._refresh_table()

    def _selected_document(self):
        if not self.selected_key or self.selected_key not in self.documents:
            self._show_snack("Veuillez sélectionner un document dans le tableau.", is_error=True)
            return None, None
        type_doc, num = self.selected_key
        return type_doc, self.documents.get(self.selected_key)

    # =========================================================================
    # ACTIONS DU MENU
    # =========================================================================
    def _creer_document(self, doc_type="devis"):
        if hasattr(self.app, "navigate_to"):
            self.app.navigate_to("CreateDocument", doc_type=doc_type)

    def ouvrir_pdf(self, doc=None):
        if not doc:
            _, doc = self._selected_document()
        if doc and hasattr(self.app, "navigate_to"):
            self.app.navigate_to("PDFViewer", doc=doc)

    def modifier_selectionne(self, e=None):
        type_doc, doc = self._selected_document()
        if doc and hasattr(self.app, "navigate_to"):
            self.app.navigate_to("CreateDocument", doc_type=type_doc, doc_to_edit=doc)

    def marquer_payee(self, e=None):
        """Passe le statut de la facture à 'Payée' avec la date du jour et déduit le stock."""
        type_doc, doc = self._selected_document()
        if not doc:
            return

        if type_doc != "facture":
            return self._show_snack("Seules les factures peuvent être marquées comme payées.", is_error=True)

        if doc.get("statut") == "Payée":
            return self._show_snack(f"Cette facture a déjà été réglée le {doc.get('date_paiement', 'inconnue')}.")

        date_aujourdhui = datetime.now().strftime("%d/%m/%Y")

        def valider(_):
            doc["statut"] = "Payée"
            doc["date_paiement"] = date_aujourdhui

            # 📦 RETRAIT DES STOCKS AUTOMATIQUE
            self._deduire_stock_pour_facture(doc)

            if hasattr(self.app, "save_data"):
                self.app.save_data()

            self._close_dialog(dialog)
            self._refresh_table()
            self._show_snack(f"Facture {doc['numero']} enregistrée comme 'Payée' et stock déduit !")

        dialog = ft.AlertDialog(
            title=ft.Text("💶 Encaissement"),
            content=ft.Text(
                f"Confirmer l'encaissement de la facture n°{doc['numero']} le {date_aujourdhui} ?\n(Le stock d'articles sera déduit)"
            ),
            actions=[
                ft.TextButton("Annuler", on_click=lambda _: self._close_dialog(dialog)),
                ft.ElevatedButton("Confirmer", bgcolor="#10B981", color="white", on_click=valider),
            ],
        )
        self._open_dialog(dialog)

    def declarer_urssaf(self, e=None):
        """Marque une facture comme déclarée à l'URSSAF."""
        type_doc, doc = self._selected_document()
        if not doc:
            return

        if type_doc != "facture":
            return self._show_snack("Seules les factures peuvent être déclarées à l'URSSAF.", is_error=True)

        if doc.get("urssaf_declare"):
            return self._show_snack("Cette facture a déjà été déclarée à l'URSSAF.")

        def valider(_):
            doc["urssaf_declare"] = True
            doc["statut"] = "Déclarée"
            if hasattr(self.app, "save_data"):
                self.app.save_data()
            self._close_dialog(dialog)
            self._refresh_table()
            self._show_snack("Facture marquée comme déclarée à l'URSSAF. ✅")

        dialog = ft.AlertDialog(
            title=ft.Text("✅ Déclaration URSSAF"),
            content=ft.Text(f"Marquer la facture n°{doc['numero']} comme déclarée à l'URSSAF ?"),
            actions=[
                ft.TextButton("Annuler", on_click=lambda _: self._close_dialog(dialog)),
                ft.ElevatedButton("Confirmer", bgcolor="#16A34A", color="white", on_click=valider),
            ],
        )
        self._open_dialog(dialog)

    def convertir_devis_en_facture(self, e=None):
        """Convertit un devis signé en facture."""
        type_doc, doc = self._selected_document()
        if not doc:
            return

        if type_doc != "devis":
            return self._show_snack("Vous devez sélectionner un devis pour effectuer cette action.", is_error=True)

        if doc.get("statut") != "Signé":
            return self._show_snack("Le devis doit être au statut 'Signé' pour être converti en facture.", is_error=True)

        nouvelle_facture = {
            "numero": self._next_invoice_number(),
            "client": doc.get("client"),
            "articles": list(doc.get("articles", [])),
            "lignes": list(doc.get("lignes", doc.get("articles", []))),
            "total_ht": doc.get("total_ht", doc.get("montant_ht", 0)),
            "montant_ht": doc.get("montant_ht", doc.get("total_ht", 0)),
            "tva": doc.get("tva", doc.get("montant_tva", 0)),
            "montant_tva": doc.get("montant_tva", doc.get("tva", 0)),
            "total_ttc": doc.get("total_ttc", doc.get("montant_ttc", 0)),
            "montant_ttc": doc.get("montant_ttc", doc.get("total_ttc", 0)),
            "date_creation": datetime.now().strftime("%d/%m/%Y"),
            "statut": "À payer",
            "urssaf_declare": False,
            "stock_deduit": False,
        }

        if not hasattr(self.app, "factures") or not isinstance(self.app.factures, list):
            self.app.factures = []

        self.app.factures.append(nouvelle_facture)
        doc["statut"] = "Accepté / Converti"

        if hasattr(self.app, "save_data"):
            self.app.save_data()

        self._refresh_table()
        self._show_snack(f"Facture {nouvelle_facture['numero']} créée avec succès à partir du devis.")

    def supprimer_selectionne(self, e=None):
        type_doc, doc = self._selected_document()
        if not doc:
            return

        def valider(_):
            if type_doc == "devis" and hasattr(self.app, "devis"):
                self.app.devis.remove(doc)
            elif type_doc == "facture" and hasattr(self.app, "factures"):
                self.app.factures.remove(doc)

            self.selected_key = None
            if hasattr(self.app, "save_data"):
                self.app.save_data()

            self._close_dialog(dialog)
            self._refresh_table()
            self._show_snack("Le document a été supprimé avec succès.")

        dialog = ft.AlertDialog(
            title=ft.Text("🗑️ Suppression"),
            content=ft.Text(f"Êtes-vous sûr de vouloir supprimer le {type_doc} n°{doc.get('numero')} ?"),
            actions=[
                ft.TextButton("Annuler", on_click=lambda _: self._close_dialog(dialog)),
                ft.ElevatedButton("Supprimer", bgcolor="#DC2626", color="white", on_click=valider),
            ],
        )
        self._open_dialog(dialog)

    # =========================================================================
    # 📦 DÉDUCTION AUTOMATIQUE DU STOCK
    # =========================================================================
    def _deduire_stock_pour_facture(self, doc):
        """Décrémente le stock de chaque article présent dans la facture."""
        if doc.get("stock_deduit"):
            return

        items = doc.get("lignes") or doc.get("articles") or []
        if not items:
            return

        if hasattr(self.app, "vue_articles") and hasattr(self.app.vue_articles, "deduire_stock_facture"):
            self.app.vue_articles.deduire_stock_facture(items)
        else:
            articles_db = getattr(self.app, "articles", [])
            for item in items:
                ref_cible = str(item.get("ref", "")).strip().lower()
                cb_cible = str(item.get("code_barre", "")).strip().lower()
                qte_vendue = int(item.get("quantite", item.get("qte", 1)))

                for art in articles_db:
                    ref_art = str(art.get("ref", "")).strip().lower()
                    cb_art = str(art.get("code_barre", "")).strip().lower()

                    if (ref_cible and ref_cible == ref_art) or (cb_cible and cb_cible == cb_art):
                        stock_actuel = int(art.get("stock", 0))
                        art["stock"] = max(0, stock_actuel - qte_vendue)
                        break

            if hasattr(self.app, "save_data"):
                self.app.save_data()

        doc["stock_deduit"] = True

    def _next_invoice_number(self):
        entreprise = getattr(self.app, "entreprise", {}) if hasattr(self.app, "entreprise") else {}
        prefix = entreprise.get("prefix_facture", f"F{datetime.now().year}-")
        maxi = 0
        for f in getattr(self.app, "factures", []):
            m = re.search(r"(\d+)$", str(f.get("numero", "")))
            if m:
                maxi = max(maxi, int(m.group(1)))
        return f"{prefix}{maxi + 1:03d}"

    # =========================================================================
    # EXPORT CSV
    # =========================================================================
    def exporter_csv(self, e=None):
        self.file_picker.save_file(
            dialog_title="Exporter l'historique comptable",
            file_name="historique_comptable.csv",
            allowed_extensions=["csv"],
        )

    def _on_csv_picked(self, e: ft.FilePickerResultEvent):
        if not e.path:
            return

        filepath = e.path
        try:
            with open(filepath, mode="w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow([
                    "Type Document",
                    "Numéro",
                    "Client",
                    "Total HT (€)",
                    "Total TTC (€)",
                    "Statut",
                    "Déclaré URSSAF",
                    "Date Création",
                    "Date Paiement",
                ])

                for devis in getattr(self.app, "devis", []):
                    nom_c = extract_client_name(devis.get("client", {}))
                    writer.writerow([
                        "Devis",
                        devis.get("numero", ""),
                        nom_c,
                        f"{float(devis.get('total_ht', devis.get('montant_ht', 0))):.2f}",
                        f"{float(devis.get('total_ttc', devis.get('montant_ttc', 0))):.2f}",
                        devis.get("statut", "-"),
                        "Non applicable",
                        devis.get("date_creation", ""),
                        "-",
                    ])

                for facture in getattr(self.app, "factures", []):
                    nom_c = extract_client_name(facture.get("client", {}))
                    writer.writerow([
                        "Facture",
                        facture.get("numero", ""),
                        nom_c,
                        f"{float(facture.get('total_ht', facture.get('montant_ht', 0))):.2f}",
                        f"{float(facture.get('total_ttc', facture.get('montant_ttc', 0))):.2f}",
                        facture.get("statut", "-"),
                        "Oui" if facture.get("urssaf_declare") else "Non",
                        facture.get("date_creation", ""),
                        facture.get("date_paiement", "-"),
                    ])

            self._show_snack(f"Export CSV réussi : {filepath}")
        except Exception as err:
            self._show_snack(f"Erreur d'exportation : {err}", is_error=True)

    # =========================================================================
    # HELPERS MODALES & NOTIFICATIONS
    # =========================================================================
    def _open_dialog(self, dialog):
        if hasattr(self.page, "open"):
            self.page.open(dialog)
        else:
            self.page.dialog = dialog
            dialog.open = True
            self.page.update()

    def _close_dialog(self, dialog):
        if hasattr(self.page, "close"):
            self.page.close(dialog)
        else:
            dialog.open = False
            self.page.update()

    def _show_snack(self, message, is_error=False):
        if self.page:
            snack = ft.SnackBar(
                content=ft.Text(message),
                bgcolor="#B91C1C" if is_error else "#15803D",
            )
            if hasattr(self.page, "open"):
                self.page.open(snack)
            else:
                self.page.snack_bar = snack
                snack.open = True
                self.page.update()
