import flet as ft


def safe_border(width=1, color="#424242"):
    """Bordure universelle sécurisée."""
    side = ft.BorderSide(width, color)
    return ft.Border(top=side, right=side, bottom=side, left=side)


class ArticlesView(ft.Container):
    """Vue Flet sécurisée pour la gestion des articles / prestations."""

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.expand = True
        self.padding = 10
        self.selected_article_index = None

        self.display_container = ft.Container(expand=True)
        self._build_interface()

    def did_mount(self):
        """Déclenché quand le contrôle est rattaché à la page."""
        if self.page:
            self.page.on_resized = self._on_screen_resize
            self._refresh_table()

    def safe_update(self):
        """Met à jour le composant uniquement s'il est rattaché à la page."""
        if self.page:
            try:
                self.update()
            except Exception:
                pass

    def _on_screen_resize(self, e):
        self._refresh_table()

    def _is_mobile(self):
        return self.page.width < 768 if self.page else False

    def _build_interface(self):
        header = ft.Row(
            controls=[
                ft.IconButton(
                    icon="arrow_back",
                    icon_color="white",
                    on_click=lambda e: self.app.navigate_to("Dashboard"),
                ),
                ft.Text("📦 Gestion des Articles", size=20, weight=ft.FontWeight.BOLD),
            ]
        )

        self.search_entry = ft.TextField(
            label="🔍 Rechercher un article...",
            bgcolor="#1A1A1C",
            height=40,
            text_size=13,
            on_change=self._refresh_table,
        )

        self.table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Désignation", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Prix U. HT", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("TVA (%)", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
            heading_row_color="#242426",
            show_checkbox_column=False,
        )

        button_style = ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))

        actions = ft.ResponsiveRow(
            controls=[
                ft.Column(
                    [
                        ft.ElevatedButton(
                            "➕ Nouvel Article",
                            bgcolor="#2B719E",
                            color="white",
                            height=38,
                            style=button_style,
                            on_click=self.ajouter_article,
                        )
                    ],
                    col={"xs": 6, "sm": 4},
                ),
                ft.Column(
                    [
                        ft.ElevatedButton(
                            "✏️ Modifier",
                            bgcolor="#F59E0B",
                            color="white",
                            height=38,
                            style=button_style,
                            on_click=self.modifier_article,
                        )
                    ],
                    col={"xs": 6, "sm": 4},
                ),
                ft.Column(
                    [
                        ft.ElevatedButton(
                            "🗑️ Supprimer",
                            bgcolor="#DC2626",
                            color="white",
                            height=38,
                            style=button_style,
                            on_click=self.supprimer_article,
                        )
                    ],
                    col={"xs": 12, "sm": 4},
                ),
            ],
            spacing=6,
        )

        self.content = ft.Column(
            controls=[header, self.search_entry, self.display_container, actions],
            spacing=10,
            expand=True,
        )

    def _refresh_table(self, e=None):
        query = (
            self.search_entry.value.strip().lower()
            if self.search_entry and self.search_entry.value
            else ""
        )
        articles = getattr(self.app, "articles", [])

        filtered = [
            (i, art)
            for i, art in enumerate(articles)
            if query in str(art.get("nom", art.get("designation", ""))).lower()
        ]

        if self._is_mobile():
            self._render_mobile(filtered)
        else:
            self._render_desktop(filtered)

        self.safe_update()

    def _render_desktop(self, articles):
        self.table.rows.clear()
        for idx, art in articles:
            row = ft.DataRow(cells=[])

            def select_handler(i=idx, r=row):
                return lambda e: self._select_row(i, r)

            nom = art.get("nom", art.get("designation", "-"))
            prix = f"{float(art.get('prix', art.get('prix_unitaire', 0))):.2f} €"
            tva = f"{art.get('tva', 20)} %"

            row.cells = [
                ft.DataCell(ft.Text(nom), on_tap=select_handler()),
                ft.DataCell(ft.Text(prix), on_tap=select_handler()),
                ft.DataCell(ft.Text(tva), on_tap=select_handler()),
            ]
            if self.selected_article_index == idx:
                row.selected = True

            self.table.rows.append(row)

        self.display_container.content = ft.Container(
            content=ft.Column([ft.Row([self.table], scroll=ft.ScrollMode.AUTO)], scroll=ft.ScrollMode.AUTO, expand=True),
            bgcolor="#141416",
            border_radius=10,
            border=safe_border(1, "#2A2A2E"),
            padding=8,
            expand=True,
        )

    def _render_mobile(self, articles):
        cards = []
        for idx, art in articles:
            is_sel = self.selected_article_index == idx
            nom = art.get("nom", art.get("designation", "-"))
            prix = f"{float(art.get('prix', art.get('prix_unitaire', 0))):.2f} €"

            def select_handler(i=idx):
                return lambda e: self._select_card(i)

            cards.append(
                ft.Container(
                    bgcolor="#1E1E22" if not is_sel else "#2A3A4E",
                    border=safe_border(1.5 if is_sel else 1, "#2B719E" if is_sel else "#2A2A32"),
                    border_radius=10,
                    padding=10,
                    on_click=select_handler(),
                    content=ft.Row(
                        [ft.Text(nom, weight=ft.FontWeight.BOLD, color="white"), ft.Text(prix, color="#10B981")],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                )
            )

        self.display_container.content = ft.ListView(controls=cards, spacing=8, expand=True)

    def _select_row(self, idx, row):
        for r in self.table.rows:
            r.selected = False
        row.selected = True
        self.selected_article_index = idx
        self.safe_update()

    def _select_card(self, idx):
        self.selected_article_index = idx
        self._refresh_table()

    def _close_dialog(self, dialog):
        dialog.open = False
        if self.page:
            self.page.update()

    def _show_snack(self, message, is_error=False):
        if self.page:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(message),
                bgcolor="#B91C1C" if is_error else "#15803D",
            )
            self.page.snack_bar.open = True
            self.page.update()

    def ajouter_article(self, e=None):
        if not self.page:
            return

        nom_field = ft.TextField(label="Désignation", autofocus=True)
        prix_field = ft.TextField(label="Prix HT (€)", value="0.00")
        tva_field = ft.TextField(label="TVA (%)", value="20.0")

        def valider(_):
            if not nom_field.value.strip():
                return
            try:
                prix = float(prix_field.value.replace(",", "."))
                tva = float(tva_field.value.replace(",", "."))
            except ValueError:
                self._show_snack("Saisie numérique invalide pour le prix ou la TVA.", is_error=True)
                return

            nouvel_art = {"nom": nom_field.value.strip(), "prix": prix, "tva": tva}
            if not hasattr(self.app, "articles") or not isinstance(self.app.articles, list):
                self.app.articles = []
            self.app.articles.append(nouvel_art)

            if hasattr(self.app, "save_data"):
                self.app.save_data()

            self._close_dialog(dialog)
            self._refresh_table()
            self._show_snack("Article ajouté avec succès.")

        dialog = ft.AlertDialog(
            title=ft.Text("➕ Nouvel Article"),
            content=ft.Column([nom_field, prix_field, tva_field], tight=True, spacing=10),
            actions=[
                ft.TextButton("Annuler", on_click=lambda _: self._close_dialog(dialog)),
                ft.ElevatedButton("Enregistrer", bgcolor="#2B719E", color="white", on_click=valider),
            ],
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def modifier_article(self, e=None):
        if self.selected_article_index is None or not hasattr(self.app, "articles"):
            return self._show_snack("Veuillez sélectionner un article à modifier.", is_error=True)
        if self.selected_article_index >= len(self.app.articles):
            return

        art = self.app.articles[self.selected_article_index]
        nom_field = ft.TextField(label="Désignation", value=str(art.get("nom", art.get("designation", ""))))
        prix_field = ft.TextField(label="Prix HT (€)", value=str(art.get("prix", art.get("prix_unitaire", 0))))
        tva_field = ft.TextField(label="TVA (%)", value=str(art.get("tva", 20)))

        def valider(_):
            if not nom_field.value.strip():
                return
            try:
                prix = float(prix_field.value.replace(",", "."))
                tva = float(tva_field.value.replace(",", "."))
            except ValueError:
                self._show_snack("Saisie numérique invalide.", is_error=True)
                return

            art["nom"] = nom_field.value.strip()
            art["prix"] = prix
            art["tva"] = tva

            if hasattr(self.app, "save_data"):
                self.app.save_data()

            self._close_dialog(dialog)
            self._refresh_table()
            self._show_snack("Article modifié.")

        dialog = ft.AlertDialog(
            title=ft.Text("✏️ Modifier l'article"),
            content=ft.Column([nom_field, prix_field, tva_field], tight=True, spacing=10),
            actions=[
                ft.TextButton("Annuler", on_click=lambda _: self._close_dialog(dialog)),
                ft.ElevatedButton("Enregistrer", bgcolor="#F59E0B", color="white", on_click=valider),
            ],
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def supprimer_article(self, e=None):
        if self.selected_article_index is None or not hasattr(self.app, "articles"):
            return self._show_snack("Veuillez sélectionner un article à supprimer.", is_error=True)
        if self.selected_article_index >= len(self.app.articles):
            return

        art = self.app.articles[self.selected_article_index]
        nom = art.get("nom", art.get("designation", "cet article"))

        def valider(_):
            self.app.articles.pop(self.selected_article_index)
            self.selected_article_index = None
            if hasattr(self.app, "save_data"):
                self.app.save_data()
            self._close_dialog(dialog)
            self._refresh_table()
            self._show_snack("Article supprimé.")

        dialog = ft.AlertDialog(
            title=ft.Text("🗑️ Suppression"),
            content=ft.Text(f"Supprimer l'article « {nom} » ?"),
            actions=[
                ft.TextButton("Annuler", on_click=lambda _: self._close_dialog(dialog)),
                ft.ElevatedButton("Supprimer", bgcolor="#DC2626", color="white", on_click=valider),
            ],
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
