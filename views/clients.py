import flet as ft


class ClientsView(ft.Container):
    def __init__(self, app):
        super().__init__(expand=True, padding=15)
        self.app = app
        self.clients = getattr(self.app, "clients", [])

        # Icône en chaîne texte brute (zéro crash Android)
        self.search_field = ft.TextField(
            hint_text="Rechercher un client...",
            prefix_icon="search",
            on_change=self._filtrer_clients,
            expand=True,
            bgcolor="#1A1A1C",
        )

        self.list_column = ft.Column(
            spacing=10, scroll=ft.ScrollMode.AUTO, expand=True
        )
        self._build_interface()

    def get_page(self):
        return self.page or getattr(self.app, "page", None)

    def safe_update(self):
        page = self.get_page()
        if page:
            try:
                page.update()
            except Exception:
                pass

    def did_mount(self):
        self.refresh_client_list()

    def _build_interface(self):
        entreprise = getattr(self.app, "entreprise", {})
        accent_color = entreprise.get("accent_color", "#2B719E")

        self.content = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("👥 Gestion des Clients", size=22, weight="bold"),
                        ft.ElevatedButton(
                            content=ft.Text("+ Nouveau Client"),
                            bgcolor=accent_color,
                            color="white",
                            on_click=lambda _: self._ouvrir_popup_client(),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Row(controls=[self.search_field]),
                ft.Container(
                    content=self.list_column,
                    expand=True,
                ),
            ],
            spacing=15,
            expand=True,
        )

    def refresh_client_list(self, filtre=""):
        self.list_column.controls.clear()
        filtre_lower = filtre.lower().strip()

        clients_a_afficher = [
            c
            for c in self.clients
            if filtre_lower in c.get("nom", "").lower()
            or filtre_lower in c.get("email", "").lower()
            or filtre_lower in c.get("ville", "").lower()
        ]

        if not clients_a_afficher:
            self.list_column.controls.append(
                ft.Container(
                    content=ft.Text(
                        "Aucun client trouvé.", color="#8E8E93", size=14
                    ),
                    padding=20,
                    alignment="center",
                )
            )
        else:
            for c in clients_a_afficher:
                self.list_column.controls.append(self._creer_carte_client(c))

        self.safe_update()

    def _filtrer_clients(self, e):
        self.refresh_client_list(e.control.value)

    def _creer_carte_client(self, client):
        adresse_complete = f"{client.get('adresse', '')} {client.get('code_postal', '')} {client.get('ville', '')}".strip()

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(
                                client.get("nom", "Sans nom"),
                                size=15,
                                weight="bold",
                            ),
                            ft.Text(
                                f"📧 {client.get('email', 'N/A')}  |  📞 {client.get('telephone', 'N/A')}",
                                size=12,
                                color="#AEAEB2",
                            ),
                            ft.Text(
                                f"📍 {adresse_complete}" if adresse_complete else "📍 Adresse non renseignée",
                                size=11,
                                color="#8E8E93",
                            ),
                        ],
                        spacing=3,
                        expand=True,
                    ),
                    ft.Row(
                        controls=[
                            ft.IconButton(
                                icon="edit",
                                icon_color="#3B82F6",
                                on_click=lambda _, c=client: self._ouvrir_popup_client(
                                    c
                                ),
                            ),
                            ft.IconButton(
                                icon="delete",
                                icon_color="#EF4444",
                                on_click=lambda _, c=client: self._supprimer_client(
                                    c
                                ),
                            ),
                        ],
                        spacing=0,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            bgcolor="#1E1E20",
            padding=12,
            border_radius=8,
            border=ft.border.all(1, "#2A2A2E"),
        )

    def _ouvrir_popup_client(self, client=None):
        est_edition = client is not None
        client_data = client or {}

        tf_nom = ft.TextField(
            label="Nom / Raison Sociale *",
            value=str(client_data.get("nom", "")),
            bgcolor="#1A1A1C",
        )
        tf_email = ft.TextField(
            label="Email",
            value=str(client_data.get("email", "")),
            bgcolor="#1A1A1C",
        )
        tf_tel = ft.TextField(
            label="Téléphone",
            value=str(client_data.get("telephone", "")),
            bgcolor="#1A1A1C",
        )
        tf_adresse = ft.TextField(
            label="Adresse",
            value=str(client_data.get("adresse", "")),
            bgcolor="#1A1A1C",
        )
        tf_cp = ft.TextField(
            label="Code Postal",
            value=str(client_data.get("code_postal", "")),
            bgcolor="#1A1A1C",
        )
        tf_ville = ft.TextField(
            label="Ville",
            value=str(client_data.get("ville", "")),
            bgcolor="#1A1A1C",
        )
        tf_siret = ft.TextField(
            label="SIRET",
            value=str(client_data.get("siret", "")),
            bgcolor="#1A1A1C",
        )

        def fermer():
            self._fermer_dialogue(dialog)

        def enregistrer(e):
            if not tf_nom.value or not tf_nom.value.strip():
                self.show_snack(
                    "Le nom du client est obligatoire !", is_error=True
                )
                return

            client_data.update(
                {
                    "nom": tf_nom.value.strip(),
                    "email": tf_email.value.strip() if tf_email.value else "",
                    "telephone": tf_tel.value.strip() if tf_tel.value else "",
                    "adresse": tf_adresse.value.strip() if tf_adresse.value else "",
                    "code_postal": tf_cp.value.strip() if tf_cp.value else "",
                    "ville": tf_ville.value.strip() if tf_ville.value else "",
                    "siret": tf_siret.value.strip() if tf_siret.value else "",
                }
            )

            if not est_edition:
                client_data["id"] = len(self.clients) + 1
                self.clients.append(client_data)

            if hasattr(self.app, "save_data"):
                self.app.save_data()

            fermer()
            self.refresh_client_list(self.search_field.value)
            self.show_snack("Client enregistré avec succès ! ✔")

        entreprise = getattr(self.app, "entreprise", {})
        accent_color = entreprise.get("accent_color", "#2B719E")

        # Container fixe à 300px avec scroll pour compatibilité clavier mobile
        dialog = ft.AlertDialog(
            title=ft.Text(
                "Éditer Client" if est_edition else "Nouveau Client",
                size=18,
                weight="bold",
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        tf_nom,
                        tf_email,
                        tf_tel,
                        tf_adresse,
                        tf_cp,
                        tf_ville,
                        tf_siret,
                    ],
                    spacing=10,
                    scroll=ft.ScrollMode.AUTO,
                ),
                width=320,
                height=300,
            ),
            actions=[
                ft.TextButton(
                    content=ft.Text("Annuler"), on_click=lambda _: fermer()
                ),
                ft.ElevatedButton(
                    content=ft.Text("Enregistrer"),
                    bgcolor=accent_color,
                    color="white",
                    on_click=enregistrer,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self._ouvrir_dialogue(dialog)

    def _supprimer_client(self, client):
        def fermer():
            self._fermer_dialogue(dialog)

        def confirmer(_):
            if client in self.clients:
                self.clients.remove(client)
                if hasattr(self.app, "save_data"):
                    self.app.save_data()
                self.refresh_client_list(self.search_field.value)
                self.show_snack("Client supprimé.")
            fermer()

        dialog = ft.AlertDialog(
            title=ft.Text("Confirmer la suppression"),
            content=ft.Text(
                f"Voulez-vous vraiment supprimer {client.get('nom')} ?"
            ),
            actions=[
                ft.TextButton(
                    content=ft.Text("Annuler"), on_click=lambda _: fermer()
                ),
                ft.ElevatedButton(
                    content=ft.Text("Supprimer"),
                    bgcolor="#B91C1C",
                    color="white",
                    on_click=confirmer,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self._ouvrir_dialogue(dialog)

    def _ouvrir_dialogue(self, dlg):
        page = self.get_page()
        if not page:
            return
        if hasattr(page, "open"):
            try:
                page.open(dlg)
                return
            except Exception:
                pass
        dlg.open = True
        if dlg not in page.overlay:
            page.overlay.append(dlg)
        page.update()

    def _fermer_dialogue(self, dlg):
        page = self.get_page()
        if not page:
            return
        if hasattr(page, "close"):
            try:
                page.close(dlg)
                return
            except Exception:
                pass
        dlg.open = False
        page.update()

    def show_snack(self, message, is_error=False):
        color = "#B91C1C" if is_error else "#15803D"
        page = self.get_page()
        if page:
            snack = ft.SnackBar(content=ft.Text(message), bgcolor=color)
            if hasattr(page, "open"):
                try:
                    page.open(snack)
                    return
                except Exception:
                    pass
            page.snack_bar = snack
            snack.open = True
            page.update()
