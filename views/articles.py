import flet as ft


class ArticlesView(ft.Container):
    def __init__(self, app):
        super().__init__(expand=True)
        self.app = app
        self.accent_color = getattr(self.app, "entreprise", {}).get(
            "accent_color", "#2B719E"
        )
        self.articles = getattr(self.app, "articles", [])
        self.current_editing_index = None

        # --- COMPOSANTS DU FORMULAIRE ---
        self.input_designation = ft.TextField(
            label="Désignation / Nom *", expand=True
        )
        self.input_reference = ft.TextField(
            label="Référence (Code art.)", expand=True
        )
        self.input_prix_ht = ft.TextField(
            label="Prix Unitaire HT (€) *",
            expand=True,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.input_tva = ft.TextField(
            label="Taux de TVA (%)",
            expand=True,
            value="20",
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        self.dropdown_unite = ft.Dropdown(
            label="Unité",
            expand=True,
            options=[
                ft.dropdown.Option("Unité"),
                ft.dropdown.Option("Heure"),
                ft.dropdown.Option("Jour"),
                ft.dropdown.Option("Forfait"),
                ft.dropdown.Option("m²"),
                ft.dropdown.Option("kg"),
                ft.dropdown.Option("ml"),
            ],
            value="Unité",
        )
        self.input_description = ft.TextField(
            label="Description détaillée",
            multiline=True,
            min_lines=2,
            max_lines=4,
            expand=True,
        )

        # --- COMPOSANTS DE L'ÉCRAN LISTE ---
        self.input_recherche = ft.TextField(
            label="Rechercher un article (désignation, référence)...",
            prefix_icon="search",
            expand=True,
            on_change=self.filtrer_articles,
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
        self.load_articles_list()

        self.view_container.content = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=15,
            expand=True,
            controls=[
                ft.Row(
                    [
                        ft.Text(
                            "📦 Prestations & Articles",
                            size=20,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.ElevatedButton(
                            "+ Nouvel Article",
                            bgcolor=self.accent_color,
                            color=ft.colors.WHITE,
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

    def afficher_ecran_formulaire(self, index_article=None):
        self.current_editing_index = index_article
        titre_form = (
            "Modifier l'article"
            if index_article is not None
            else "Créer une fiche article"
        )

        if index_article is not None:
            self.pre_remplir_formulaire(index_article)
        else:
            self.vider_formulaire()

        self.view_container.content = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=20,
            controls=[
                ft.Row(
                    [
                        ft.Text(
                            titre_form, size=18, weight=ft.FontWeight.BOLD
                        ),
                        ft.Container(expand=True),
                        ft.OutlinedButton(
                            "Retour",
                            on_click=lambda e: self.afficher_ecran_liste(),
                        ),
                    ]
                ),
                ft.Divider(),
                self.creer_section_card(
                    "1. Identification de l'Article",
                    [
                        ft.ResponsiveRow(
                            [
                                ft.Container(
                                    self.input_designation,
                                    col={"sm": 12, "md": 8},
                                ),
                                ft.Container(
                                    self.input_reference,
                                    col={"sm": 12, "md": 4},
                                ),
                            ]
                        )
                    ],
                ),
                self.creer_section_card(
                    "2. Tarification & Taxe",
                    [
                        ft.ResponsiveRow(
                            [
                                ft.Container(
                                    self.input_prix_ht, col={"sm": 12, "md": 4}
                                ),
                                ft.Container(
                                    self.input_tva, col={"sm": 12, "md": 4}
                                ),
                                ft.Container(
                                    self.dropdown_unite, col={"sm": 12, "md": 4}
                                ),
                            ]
                        )
                    ],
                ),
                self.creer_section_card(
                    "3. Description Complémentaire",
                    [ft.Row([self.input_description])],
                ),
                ft.Row(
                    [
                        ft.TextButton(
                            "Annuler",
                            on_click=lambda e: self.afficher_ecran_liste(),
                        ),
                        ft.ElevatedButton(
                            "Enregistrer",
                            bgcolor=ft.colors.GREEN_700,
                            color=ft.colors.WHITE,
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
                    ft.Text(
                        titre,
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=ft.colors.BLUE_200,
                    ),
                    ft.Divider(color=ft.colors.GREY_800, height=8),
                    ft.Column(controls=composants, spacing=10),
                ],
                spacing=5,
            ),
        )

    # ============================================================
    # 🛠️ GESTION DES DONNÉES (CRUD)
    # ============================================================

    def load_articles_list(self, filtre_texte=""):
        self.list_column.controls.clear()
        filtre_lower = filtre_texte.lower().strip()

        articles_filtrés = [
            (idx, a)
            for idx, a in enumerate(self.articles)
            if filtre_lower in a.get("designation", "").lower()
            or filtre_lower in a.get("reference", "").lower()
        ]

        if not articles_filtrés:
            self.list_column.controls.append(
                ft.Container(
                    content=ft.Text(
                        "Aucun article trouvé.",
                        color=ft.colors.GREY_400,
                        size=14,
                    ),
                    padding=20,
                )
            )
        else:
            for idx, a in articles_filtrés:
                self.list_column.controls.append(
                    self.creer_carte_article(idx, a)
                )

    def creer_carte_article(self, index, article):
        try:
            prix_ht = float(article.get("prix_ht", 0.0))
        except (ValueError, TypeError):
            prix_ht = 0.0

        try:
            tva = float(article.get("tva", 20.0))
        except (ValueError, TypeError):
            tva = 20.0

        prix_ttc = prix_ht * (1 + tva / 100)

        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(
                                        article.get("designation", "Sans nom"),
                                        size=15,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Container(
                                        content=ft.Text(
                                            article.get(
                                                "reference", "RÉF-N/A"
                                            ),
                                            size=10,
                                            color=ft.colors.GREY_300,
                                        ),
                                        bgcolor="#374151",
                                        padding=ft.padding.symmetric(
                                            horizontal=6, vertical=2
                                        ),
                                        border_radius=4,
                                    ),
                                ],
                                spacing=8,
                            ),
                            ft.Text(
                                f"Prix HT : {prix_ht:.2f} €  |  TVA : {tva}%  |  TTC : {prix_ttc:.2f} € ({article.get('unite', 'Unité')})",
                                size=12,
                                color=ft.colors.GREY_300,
                            ),
                            ft.Text(
                                article.get("description", ""),
                                size=11,
                                color=ft.colors.GREY_400,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                        spacing=3,
                        expand=True,
                    ),
                    ft.Row(
                        controls=[
                            ft.IconButton(
                                icon="edit",
                                icon_color=ft.colors.BLUE_300,
                                on_click=lambda e, idx=index: self.afficher_ecran_formulaire(
                                    idx
                                ),
                            ),
                            ft.IconButton(
                                icon="delete",
                                icon_color=ft.colors.RED_400,
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
        page_obj = self.page or getattr(self.app, "page", None)

        if (
            not self.input_designation.value
            or not self.input_designation.value.strip()
        ):
            if page_obj:
                page_obj.snack_bar = ft.SnackBar(
                    content=ft.Text("La désignation de l'article est obligatoire !"),
                    bgcolor=ft.colors.RED_700,
                )
                page_obj.snack_bar.open = True
                page_obj.update()
            return

        try:
            val_ht = (
                self.input_prix_ht.value.replace(" ", "")
                .replace(",", ".")
                .strip()
                if self.input_prix_ht.value
                else "0"
            )
            prix_ht = float(val_ht) if val_ht else 0.0
        except ValueError:
            if page_obj:
                page_obj.snack_bar = ft.SnackBar(
                    content=ft.Text("Veuillez saisir un prix HT valide."),
                    bgcolor=ft.colors.RED_700,
                )
                page_obj.snack_bar.open = True
                page_obj.update()
            return

        try:
            val_tva = (
                self.input_tva.value.replace(" ", "").replace(",", ".").strip()
                if self.input_tva.value
                else "0"
            )
            tva = float(val_tva) if val_tva else 0.0
        except ValueError:
            if page_obj:
                page_obj.snack_bar = ft.SnackBar(
                    content=ft.Text("Veuillez saisir un taux de TVA valide."),
                    bgcolor=ft.colors.RED_700,
                )
                page_obj.snack_bar.open = True
                page_obj.update()
            return

        dict_article = {
            "designation": self.input_designation.value.strip(),
            "reference": self.input_reference.value.strip()
            if self.input_reference.value
            else "",
            "prix_ht": prix_ht,
            "tva": tva,
            "unite": self.dropdown_unite.value or "Unité",
            "description": self.input_description.value.strip()
            if self.input_description.value
            else "",
        }

        if self.current_editing_index is not None:
            self.articles[self.current_editing_index] = dict_article
        else:
            dict_article["id"] = len(self.articles) + 1
            self.articles.append(dict_article)

        if hasattr(self.app, "save_data"):
            self.app.save_data()

        self.afficher_ecran_liste()

    def supprimer_fiche(self, index):
        page_obj = self.page or getattr(self.app, "page", None)

        def confirmer_suppression(e):
            if index < len(self.articles):
                self.articles.pop(index)
                if hasattr(self.app, "save_data"):
                    self.app.save_data()
            dialog_confirmation.open = False
            if page_obj:
                page_obj.update()
            self.afficher_ecran_liste()

        dialog_confirmation = ft.AlertDialog(
            title=ft.Text("⚠️ Suppression", size=16),
            content=ft.Text(
                f"Supprimer l'article '{self.articles[index].get('designation')}' ?"
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
                    bgcolor=ft.colors.RED_700,
                    color=ft.colors.WHITE,
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

    def filtrer_articles(self, e):
        txt = self.input_recherche.value or ""
        self.load_articles_list(filtre_texte=txt)
        if self.page:
            self.list_column.update()

    def pre_remplir_formulaire(self, index):
        a = self.articles[index]
        self.input_designation.value = str(a.get("designation", ""))
        self.input_reference.value = str(a.get("reference", ""))
        self.input_prix_ht.value = str(a.get("prix_ht", ""))
        self.input_tva.value = str(a.get("tva", "20"))
        self.dropdown_unite.value = str(a.get("unite", "Unité"))
        self.input_description.value = str(a.get("description", ""))

    def vider_formulaire(self):
        self.input_designation.value = ""
        self.input_reference.value = ""
        self.input_prix_ht.value = ""
        self.input_tva.value = "20"
        self.dropdown_unite.value = "Unité"
        self.input_description.value = ""
