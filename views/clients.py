import flet as ft


def safe_border(width=1, color="#424242"):
    """Bordure universelle sécurisée."""
    side = ft.BorderSide(width, color)
    return ft.Border(top=side, right=side, bottom=side, left=side)


class ClientsView(ft.Container):
    """Vue Flet sécurisée pour la gestion du répertoire clients."""

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.expand = True
        self.padding = 10
        self.selected_client_index = None

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
                ft.Text("👥 Répertoire Clients", size=20, weight=ft.FontWeight.BOLD),
            ]
        )

        self.search_entry = ft.TextField(
            label="🔍 Rechercher un client...",
            bgcolor="#1A1A1C",
            height=40,
            text_size=13,
            on_change=self._refresh_table,
        )

        self.table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Nom / Entreprise", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Email", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Téléphone", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Ville", weight=ft.FontWeight.BOLD)),
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
                            "➕ Nouveau Client",
                            bgcolor="#2B719E",
                            color="white",
                            height=38,
                            style=button_style,
                            on_click=self.ajouter_client,
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
                            on_click=self.modifier_client,
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
                            on_click=self.supprimer_client,
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
        clients = getattr(self.app, "clients", [])

        filtered = []
        for i, cli in enumerate(clients):
            nom = cli.get("nom", "") if isinstance(cli, dict) else str(cli)
            email = cli.get("email", "") if isinstance(cli, dict) else ""
            if query in nom.lower() or query in email.lower():
                filtered.append((i, cli))

        if self._is_mobile():
            self._render_mobile(filtered)
        else:
            self._render_desktop(filtered)

        self.safe_update()

    def _render_desktop(self, clients):
        self.table.rows.clear()
        for idx, cli in clients:
            row = ft.DataRow(cells=[])

            def select_handler(i=idx, r=row):
                return lambda e: self._select_row(i, r)

            nom = cli.get("nom", "Inconnu") if isinstance(cli, dict) else str(cli)
            email = cli.get("email", "-") if isinstance(cli, dict) else "-"
            tel = cli.get("telephone", cli.get("tel", "-")) if isinstance(cli, dict) else "-"
            ville = cli.get("ville", "-") if isinstance(cli, dict) else "-"

            row.cells = [
                ft.DataCell(ft.Text(nom), on_tap=select_handler()),
                ft.DataCell(ft.Text(email), on_tap=select_handler()),
                ft.DataCell(ft.Text(tel), on_tap=select_handler()),
                ft.DataCell(ft.Text(ville), on_tap=select_handler()),
            ]
            self.table.rows.append(row)

        self.display_container.content = ft.Container(
            content=ft.Column([ft.Row([self.table], scroll=ft.ScrollMode.AUTO)], scroll=ft.ScrollMode.AUTO, expand=True),
            bgcolor="#141416",
            border_radius=10,
            border=safe_border(1, "#2A2A2E"),
            padding=8,
            expand=True,
        )

    def _render_mobile(self, clients):
        cards = []
        for idx, cli in clients:
            is_sel = self.selected_client_index == idx
            nom = cli.get("nom", "Inconnu") if isinstance(cli, dict) else str(cli)
            email = cli.get("email", "-") if isinstance(cli, dict) else "-"

            def select_handler(i=idx):
                return lambda e: self._select_card(i)

            cards.append(
                ft.Container(
                    bgcolor="#1E1E22" if not is_sel else "#2A3A4E",
                    border=safe_border(1.5 if is_sel else 1, "#2B719E" if is_sel else "#2A2A32"),
                    border_radius=10,
                    padding=10,
                    on_click=select_handler(),
                    content=ft.Column(
                        [
                            ft.Text(nom, weight=ft.FontWeight.BOLD, color="white"),
                            ft.Text(email, size=11, color="#AEAEB2"),
                        ],
                        spacing=4,
                    ),
                )
            )

        self.display_container.content = ft.ListView(controls=cards, spacing=8, expand=True)

    def _select_row(self, idx, row):
        for r in self.table.rows:
            r.selected = False
        row.selected = True
        self.selected_client_index = idx
        self.safe_update()

    def _select_card(self, idx):
        self.selected_client_index = idx
        self._refresh_table()

    def ajouter_client(self, e=None):
        pass

    def modifier_client(self, e=None):
        pass

    def supprimer_client(self, e=None):
        pass
