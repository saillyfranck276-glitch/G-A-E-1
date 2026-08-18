import flet as ft


class ArticlesView(ft.Container):
    def __init__(self, app):
        super().__init__(expand=True, padding=15)
        self.app = app
        self.articles = getattr(self.app, "articles", [])

        # Utilisation d'une chaîne pure pour l'icône de recherche (évite tout crash sur Android)
        self.search_field = ft.TextField(
            hint_text="Rechercher un article...",
            prefix_icon="search",
            on_change=self._filtrer_articles,
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
        self.refresh_article_list()

    def _build_interface(self):
        entreprise = getattr(self.app, "entreprise", {})
        accent_color = entreprise.get("accent_color", "#2B719E")

        self.content = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(
                            "📦 Prestations & Articles", size=22, weight="bold"
                        ),
                        ft.ElevatedButton(
                            content=ft.Text("+ Nouvel Article"),
                            bgcolor=accent_color,
                            color="white",
                            on_click=lambda _: self._ouvrir_popup_article(),
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

    def refresh_article_list(self, filtre=""):
        self.list_column.controls.clear()
        filtre_lower = filtre.lower().strip()

        articles_a_afficher = [
            a
            for a in self.articles
            if filtre_lower in a.get("designation", "").lower()
            or filtre_lower in a.get("reference", "").lower()
        ]

        if not articles_a_afficher:
            self.list_column.controls.append(
                ft.Container(
                    content=ft.Text(
                        "Aucun article trouvé.", color="#8E8E93", size=14
                    ),
                    padding=20,
                    alignment="center",
                )
            )
        else:
            for a in articles_a_afficher:
                self.list_column.controls.append(self._creer_carte_article(a))

        self.safe_update()

    def _filtrer_articles(self, e):
        self.refresh_article_list(e.control.value)

    def _creer_carte_article(self, article):
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
                                        weight="bold",
                                    ),
                                    ft.Container(
                                        content=ft.Text(
                                            article.get("reference", "RÉF-N/A"),
                                            size=10,
                                            color="#AEAEB2",
                                        ),
                                        bgcolor="#2A2A2E",
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
                                color="#AEAEB2",
                            ),
                            ft.Text(
                                article.get("description", ""),
                                size=11,
                                color="#8E8E93",
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
                                icon_color="#3B82F6",
                                on_click=lambda _, a=article: self._ouvrir_popup_article(
                                    a
                                ),
                            ),
                            ft.IconButton(
                                icon="delete",
                                icon_color="#EF4444",
                                on_click=lambda _, a=article: self._supprimer_article(
                                    a
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

    def _ouvrir_popup_article(self, article=None):
        est_edition = article is not None
        art_data = article or {}

        tf_ref = ft.TextField(
            label="Référence",
            value=str(art_data.get("reference", "")),
            bgcolor="#1A1A1C",
        )
        tf_desig = ft.TextField(
            label="Désignation / Nom *",
            value=str(art_data.get("designation", "")),
            bgcolor="#1A1A1C",
        )
        tf_prix_ht = ft.TextField(
            label="Prix Unitaire HT (€) *",
            value=str(art_data.get("prix_ht", "")),
            keyboard_type=ft.KeyboardType.NUMBER,
            bgcolor="#1A1A1C",
        )
        tf_tva = ft.TextField(
            label="Taux de TVA (%)",
            value=str(art_data.get("tva", "20")),
            keyboard_type=ft.KeyboardType.NUMBER,
            bgcolor="#1A1A1C",
        )
        dd_unite = ft.Dropdown(
            label="Unité",
            options=[
                ft.dropdown.Option(u)
                for u in ["Unité", "Heure", "Jour", "Forfait", "m²", "kg", "ml"]
            ],
            value=str(art_data.get("unite", "Unité")),
            bgcolor="#1A1A1C",
        )
        tf_desc = ft.TextField(
            label="Description détaillée",
            value=str(art_data.get("description", "")),
            multiline=True,
            min_lines=2,
            max_lines=3,
            bgcolor="#1A1A1C",
        )

        def fermer():
            self._fermer_dialogue(dialog)

        def enregistrer(e):
            if not tf_desig.value or not tf_desig.value.strip():
                self.show_snack(
                    "La désignation de l'article est obligatoire !",
                    is_error=True,
                )
                return

            try:
                val_ht = (
                    tf_prix_ht.value.replace(" ", "").replace(",", ".").strip()
                )
                prix_ht = float(val_ht) if val_ht else 0.0
            except ValueError:
                self.show_snack(
                    "Saisissez un prix HT valide.", is_error=True
                )
                return

            try:
                val_tva = (
                    tf_tva.value.replace(" ", "").replace(",", ".").strip()
                )
                tva = float(val_tva) if val_tva else 0.0
            except ValueError:
                self.show_snack(
                    "Saisissez un taux de TVA valide.", is_error=True
                )
                return

            art_data.update(
                {
                    "reference": tf_ref.value.strip() if tf_ref.value else "",
                    "designation": tf_desig.value.strip(),
                    "prix_ht": prix_ht,
                    "tva": tva,
                    "unite": dd_unite.value or "Unité",
                    "description": tf_desc.value.strip() if tf_desc.value else "",
                }
            )

            if not est_edition:
                art_data["id"] = len(self.articles) + 1
                self.articles.append(art_data)

            if hasattr(self.app, "save_data"):
                self.app.save_data()

            fermer()
            self.refresh_article_list(self.search_field.value)
            self.show_snack("Article sauvegardé avec succès ! ✔")

        entreprise = getattr(self.app, "entreprise", {})
        accent_color = entreprise.get("accent_color", "#2B719E")

        # Container fixe à 300px pour garder 'Enregistrer' visible malgré le clavier mobile
        dialog = ft.AlertDialog(
            title=ft.Text(
                "Modifier l'Article" if est_edition else "Nouvel Article",
                size=18,
                weight="bold",
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        tf_desig,
                        tf_ref,
                        tf_prix_ht,
                        tf_tva,
                        dd_unite,
                        tf_desc,
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

    def _supprimer_article(self, article):
        def fermer():
            self._fermer_dialogue(dialog)

        def confirmer(_):
            if article in self.articles:
                self.articles.remove(article)
                if hasattr(self.app, "save_data"):
                    self.app.save_data()
                self.refresh_article_list(self.search_field.value)
                self.show_snack("Article supprimé.")
            fermer()

        dialog = ft.AlertDialog(
            title=ft.Text("Confirmer la suppression"),
            content=ft.Text(
                f"Voulez-vous supprimer l'article '{article.get('designation')}' ?"
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
