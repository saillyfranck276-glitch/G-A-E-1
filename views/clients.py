import flet as ft


class ClientsView(ft.Container):
    def __init__(self, app):
        super().__init__(expand=True)
        self.app = app
        self.accent_color = getattr(self.app, "entreprise", {}).get(
            "accent_color", "#2B719E"
        )
        self.clients = getattr(self.app, "clients", [])
        self.current_editing_index = None

        # --- COMPOSANTS DU FORMULAIRE ---
        self.input_nom = ft.TextField(
            label="Nom / Raison Sociale *", expand=True
        )
        self.input_email = ft.TextField(
            label="Adresse Email",
            expand=True,
            keyboard_type=ft.KeyboardType.EMAIL,
        )
        self.input_telephone = ft.TextField(
            label="Téléphone",
            expand=True,
            keyboard_type=ft.KeyboardType.PHONE,
        )
        self.input_adresse = ft.TextField(
            label="Adresse (Rue / Voie)", expand=True
        )
        self.input_cp = ft.TextField(
            label="Code Postal",
            expand=True,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.input_ville = ft.TextField(label="Ville", expand=True)
        self.input_siret = ft.TextField(label="N° SIRET", expand=True)

        # --- COMPOSANTS DE L'ÉCRAN LISTE ---
        self.input_recherche = ft.TextField(
            label="Rechercher un client (nom, email, ville)...",
            prefix_icon="search",
            expand=True,
            on_change=self.filtrer_clients,
        )

        self.list_column = ft.Column(spacing=10, expand=True)
        self.view_container = ft.Container(expand=True)
        self.content = ft.Column([self.view_container], expand=True)

        self.afficher_ecran_liste()

    # ============================================================
    # 🖥️ GESTION DES ÉCRANS (LISTE ↔ FORMULAIRE)
    # ============================================================

    def afficher_ecran_liste(self):
        self.current_editing_index = None
        self.load_clients_list()

        self.view_container.content = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=15,
            expand=True,
            controls=[
                ft.Row(
                    [
                        ft.Text("👥 Gestion des Clients", size=20, weight="bold"),
                        ft.ElevatedButton(
                            "+ Nouveau Client",
                            bgcolor=self.accent_color,
                            color="white",
                            height=44,
                            on_click=lambda e: self.afficher_ecran_formulaire(),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Divider(),
                ft.Row([self.input_recherche]),
                ft.Container(
                    bgcolor="#1F2937",
                    padding=10,
                    border_radius=10,
                    expand=True,
                    content=self.list_column,
                ),
            ],
        )
        if self.page:
            self.update()

    def afficher_ecran_formulaire(self, index_client=None):
        self.current_editing_index = index_client
        titre_form = (
            "Modifier le client"
            if index_client is not None
            else "Créer une fiche client"
        )

        if index_client is not None:
            self.pre_remplir_formulaire(index_client)
        else:
            self.vider_formulaire()

        self.view_container.content = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=20,
            controls=[
                ft.Row(
                    [
                        ft.Text(titre_form, size=18, weight="bold"),
                        ft.Container(expand=True),
                        ft.OutlinedButton(
                            "Retour",
                            on_click=lambda e: self.afficher_ecran_liste(),
                        ),
                    ]
                ),
                ft.Divider(),
                self.creer_section_card(
                    "1. Identité & Informations Légales",
                    [
                        ft.ResponsiveRow(
                            [
                                ft.Container(
                                    self.input_nom, col={"sm": 12, "md": 8}
                                ),
                                ft.Container(
                                    self.input_siret, col={"sm": 12, "md": 4}
                                ),
                            ]
                        )
                    ],
                ),
                self.creer_section_card(
                    "2. Coordonnées de Contact",
                    [
                        ft.ResponsiveRow(
                            [
                                ft.Container(
                                    self.input_email, col={"sm": 12, "md": 6}
                                ),
                                ft.Container(
                                    self.input_telephone,
                                    col={"sm": 12, "md": 6},
                                ),
                            ]
                        )
                    ],
                ),
                self.creer_section_card(
                    "3. Adresse de Facturation",
                    [
                        ft.Row([self.input_adresse]),
                        ft.ResponsiveRow(
                            [
                                ft.Container(
                                    self.input_cp, col={"sm": 12, "md": 4}
                                ),
                                ft.Container(
                                    self.input_ville, col={"sm": 12, "md": 8}
                                ),
                            ]
                        ),
                    ],
                ),
                ft.Row(
                    [
                        ft.TextButton(
                            "Annuler",
                            on_click=lambda e: self.afficher_ecran_liste(),
                        ),
                        ft.ElevatedButton(
                            "Enregistrer",
                            bgcolor="#15803D",
                            color="white",
                            height=48,
                            on_click=self.sauvegarder_fiche,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    spacing=10,
                ),
                ft.Container(height=20),
            ],
        )
        if self.page:
            self.update()

    def creer_section_card(self, titre, composants):
        return ft.Container(
            bgcolor="#1F2937",
            padding=15,
            border_radius=10,
            content=ft.Column(
                [
                    ft.Text(titre, size=14, weight="bold", color="#BFDBFE"),
                    ft.Divider(color="#374151", height=8),
                    ft.Column(controls=composants, spacing=10),
                ],
                spacing=5,
            ),
        )

    # ============================================================
    # 🛠️ GESTION DES DONNÉES (CRUD)
    # ============================================================

    def load_clients_list(self, filtre_texte=""):
        self.list_column.controls.clear()
        filtre_lower = filtre_texte.lower().strip()

        clients_filtrés = [
            (idx, c)
            for idx, c in enumerate(self.clients)
            if filtre_lower in c.get("nom", "").lower()
            or filtre_lower in c.get("email", "").lower()
            or filtre_lower in c.get("ville", "").lower()
        ]

        if not clients_filtrés:
            self.list_column.controls.append(
                ft.Container(
                    content=ft.Text(
                        "Aucun client trouvé.", color="#9CA3AF", size=14
                    ),
                    padding=20,
                )
            )
        else:
            for idx, c in clients_filtrés:
                self.list_column.controls.append(
                    self.creer_carte_client(idx, c)
                )

    def creer_carte_client(self, index, client):
        adresse = f"{client.get('adresse', '')} {client.get('code_postal', '')} {client.get('ville', '')}".strip()

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
                                color="#D1D5DB",
                            ),
                            ft.Text(
                                f"📍 {adresse}"
                                if adresse
                                else "📍 Adresse non renseignée",
                                size=11,
                                color="#9CA3AF",
                            ),
                        ],
                        spacing=3,
                        expand=True,
                    ),
                    ft.Row(
                        controls=[
                            ft.IconButton(
                                icon="edit",
                                icon_color="#93C5FD",
                                on_click=lambda e, idx=index: self.afficher_ecran_formulaire(
                                    idx
                                ),
                            ),
                            ft.IconButton(
                                icon="delete",
                                icon_color="#F87171",
                                on_click=lambda e, idx=index: self.supprimer_fiche(
                                    idx
                                ),
                            ),
                        ],
                        spacing=0,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            bgcolor="#111827",
            padding=12,
            border_radius=8,
            border=ft.border.all(1, "#374151"),
        )

    def sauvegarder_fiche(self, e):
        if not self.input_nom.value or not self.input_nom.value.strip():
            page_obj = self.page or getattr(self.app, "page", None)
            if page_obj:
                page_obj.snack_bar = ft.SnackBar(
                    content=ft.Text("Le nom du client est obligatoire !"),
                    bgcolor="#B91C1C",
                )
                page_obj.snack_bar.open = True
                page_obj.update()
            return

        dict_client = {
            "nom": self.input_nom.value.strip(),
            "email": self.input_email.value.strip() if self.input_email.value else "",
            "telephone": self.input_telephone.value.strip() if self.input_telephone.value else "",
            "adresse": self.input_adresse.value.strip() if self.input_adresse.value else "",
            "code_postal": self.input_cp.value.strip() if self.input_cp.value else "",
            "ville": self.input_ville.value.strip() if self.input_ville.value else "",
            "siret": self.input_siret.value.strip() if self.input_siret.value else "",
        }

        if self.current_editing_index is not None:
            self.clients[self.current_editing_index] = dict_client
        else:
            dict_client["id"] = len(self.clients) + 1
            self.clients.append(dict_client)

        if hasattr(self.app, "save_data"):
            self.app.save_data()

        self.afficher_ecran_liste()

    def supprimer_fiche(self, index):
        page_obj = self.page or getattr(self.app, "page", None)

        def confirmer_suppression(e):
            if index < len(self.clients):
                self.clients.pop(index)
                if hasattr(self.app, "save_data"):
                    self.app.save_data()
            dialog_confirmation.open = False
            if page_obj:
                page_obj.update()
            self.afficher_ecran_liste()

        dialog_confirmation = ft.AlertDialog(
            title=ft.Text("⚠️ Suppression", size=16),
            content=ft.Text(
                f"Supprimer le client '{self.clients[index].get('nom')}' ?"
            ),
            actions=[
                ft.TextButton(
                    "Annuler",
                    on_click=lambda e: setattr(
                        dialog_confirmation, "open", False
                    )
                    or page_obj.update(),
                ),
                ft.ElevatedButton(
                    "Supprimer",
                    bgcolor="#B91C1C",
                    color="white",
                    on_click=confirmer_suppression,
                ),
            ],
        )
        if page_obj:
            if dialog_confirmation not in page_obj.overlay:
                page_obj.overlay.append(dialog_confirmation)
            dialog_confirmation.open = True
            page_obj.update()

    # ============================================================
    # ⚙️ FONCTIONS AUXILIAIRES
    # ============================================================

    def filtrer_clients(self, e):
        txt = self.input_recherche.value or ""
        self.load_clients_list(filtre_texte=txt)
        if self.page:
            self.list_column.update()

    def pre_remplir_formulaire(self, index):
        c = self.clients[index]
        self.input_nom.value = c.get("nom", "")
        self.input_email.value = c.get("email", "")
        self.input_telephone.value = c.get("telephone", "")
        self.input_adresse.value = c.get("adresse", "")
        self.input_cp.value = c.get("code_postal", "")
        self.input_ville.value = c.get("ville", "")
        self.input_siret.value = c.get("siret", "")

    def vider_formulaire(self):
        self.input_nom.value = ""
        self.input_email.value = ""
        self.input_telephone.value = ""
        self.input_adresse.value = ""
        self.input_cp.value = ""
        self.input_ville.value = ""
        self.input_siret.value = ""
