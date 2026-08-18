import flet as ft


def safe_border(width=1, color="#2A2A32"):
    """Bordure universelle sécurisée compatible Desktop et Mobile."""
    side = ft.BorderSide(width, color)
    return ft.Border(top=side, right=side, bottom=side, left=side)


class ArticlesView(ft.Container):
    """Vue Flet complète et sécurisée pour la gestion des articles et du stock."""

    def __init__(self, app):
        super().__init__(expand=True)
        self.app = app

        # Récupération de la couleur d'accentuation
        self.entreprise_data = getattr(
            self.app, "entreprise", getattr(self.app, "association", {})
        )
        self.accent_color = self.entreprise_data.get("accent_color", "#2B719E")

        self.list_container = ft.Column(spacing=10, scroll="auto", expand=True)

        self._build_interface()

    def get_page(self):
        """Récupère l'instance active de la page Flet."""
        return self.page or getattr(self.app, "page", None)

    def safe_update(self):
        """Mise à jour sécurisée de l'UI."""
        page_obj = self.get_page()
        if page_obj:
            try:
                page_obj.update()
            except Exception:
                pass

    def did_mount(self):
        """Initialisation à l'affichage de la vue."""
        self.refresh_list()

    def _build_interface(self):
        # Champ de recherche
        self.search_input = ft.TextField(
            hint_text="Rechercher par désignation, référence ou catégorie...",
            prefix_icon=ft.Icons.SEARCH if hasattr(ft, "Icons") else "search",
            on_change=self.on_search_change,
            expand=True,
            bgcolor="#1A1A1C",
            height=45,
            text_size=13,
        )

        icon_add = ft.Icons.ADD if hasattr(ft, "Icons") else "add"

        # Bouton d'ajout d'article (icône intégrée dans content)
        self.btn_add = ft.ElevatedButton(
            content=ft.Row(
                [
                    ft.Icon(icon_add, size=18, color="white"),
                    ft.Text("Nouveau Produit / Article"),
                ],
                tight=True,
                spacing=6,
            ),
            bgcolor=self.accent_color,
            color="white",
            height=40,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
            on_click=self.ouvrir_dialogue_article,
        )

        header_row = ft.Row(
            [
                ft.Text("📦 Gestion des Articles & Stock", size=18, weight="bold"),
                self.btn_add,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        self.content = ft.Container(
            padding=15,
            content=ft.Column(
                [
                    header_row,
                    ft.Row([self.search_input]),
                    ft.Divider(color="#2A2A32"),
                    self.list_container,
                ],
                spacing=12,
                expand=True,
            ),
        )

    def refresh_list(self, filter_text=""):
        """Rafraîchit la liste des articles avec filtre."""
        try:
            self.list_container.controls.clear()
            articles_raw = getattr(self.app, "articles", [])
            articles = articles_raw if isinstance(articles_raw, list) else []

            query = filter_text.lower().strip()

            filtered_articles = [
                a
                for a in articles
                if query in str(a.get("designation", "")).lower()
                or query in str(a.get("reference", "")).lower()
                or query in str(a.get("categorie", "")).lower()
            ]

            if not filtered_articles:
                self.list_container.controls.append(
                    ft.Container(
                        padding=20,
                        alignment=ft.alignment.center,
                        content=ft.Text(
                            "Aucun article trouvé.", color="#AEAEB2", italic=True
                        ),
                    )
                )
                self.safe_update()
                return

            for article in filtered_articles:
                card = self._build_article_card(article)
                self.list_container.controls.append(card)

            self.safe_update()
        except Exception as ex:
            print(f"Erreur refresh_list : {ex}")

    def _build_article_card(self, article):
        """Construit une carte d'article robuste et responsive."""
        ref = article.get("reference", "N/A")
        designation = article.get("designation", "Sans nom")
        categorie = article.get("categorie", "Général")

        try:
            prix_ht = float(article.get("prix_ht", 0.0))
        except (ValueError, TypeError):
            prix_ht = 0.0

        prix_ttc = article.get("prix_ttc", round(prix_ht * 1.2, 2))
        try:
            prix_ttc = float(prix_ttc)
        except (ValueError, TypeError):
            prix_ttc = 0.0

        try:
            stock = int(article.get("stock", 0))
        except (ValueError, TypeError):
            stock = 0

        stock_color = (
            "#34D399" if stock > 5 else ("#F59E0B" if stock > 0 else "#EF4444")
        )

        icon_edit = ft.Icons.EDIT if hasattr(ft, "Icons") else "edit"
        icon_delete = ft.Icons.DELETE if hasattr(ft, "Icons") else "delete"

        return ft.Container(
            padding=12,
            bgcolor="#1e293b",
            border_radius=8,
            border=safe_border(1, "#2A2A32"),
            content=ft.ResponsiveRow(
                [
                    ft.Column(
                        [
                            ft.Text(f"{designation}", weight="bold", size=15, color="white"),
                            ft.Text(
                                f"Réf: {ref} | Catégorie: {categorie}",
                                size=12,
                                color="#AEAEB2",
                            ),
                        ],
                        col={"xs": 12, "sm": 5},
                        spacing=4,
                    ),
                    ft.Column(
                        [
                            ft.Text(
                                f"{prix_ttc:.2f} € TTC",
                                weight="bold",
                                size=14,
                                color="#93C5FD",
                            ),
                            ft.Text(f"({prix_ht:.2f} € HT)", size=11, color="#AEAEB2"),
                        ],
                        col={"xs": 6, "sm": 3},
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                        spacing=2,
                    ),
                    ft.Column(
                        [
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                bgcolor="#0f172a",
                                border_radius=6,
                                content=ft.Text(
                                    f"Stock: {stock}",
                                    size=12,
                                    weight="bold",
                                    color=stock_color,
                                ),
                            ),
                        ],
                        col={"xs": 6, "sm": 2},
                        alignment=ft.alignment.center,
                    ),
                    ft.Row(
                        [
                            ft.IconButton(
                                icon=icon_edit,
                                icon_size=18,
                                icon_color="white",
                                tooltip="Modifier",
                                on_click=lambda e, a=article: self.ouvrir_dialogue_article(e, a),
                            ),
                            ft.IconButton(
                                icon=icon_delete,
                                icon_size=18,
                                icon_color="#EF4444",
                                tooltip="Supprimer",
                                on_click=lambda e, a=article: self.supprimer_article(e, a),
                            ),
                        ],
                        col={"xs": 12, "sm": 2},
                        alignment=ft.MainAxisAlignment.END,
                        spacing=0,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def on_search_change(self, e):
        self.refresh_list(self.search_input.value or "")

    def ouvrir_dialogue_article(self, e=None, article=None):
        is_edit = article is not None

        ref_field = ft.TextField(
            label="Référence",
            value=str(article.get("reference", "")) if is_edit else "",
            col={"xs": 12, "sm": 6},
            bgcolor="#1A1A1C",
        )
        des_field = ft.TextField(
            label="Désignation",
            value=str(article.get("designation", "")) if is_edit else "",
            col={"xs": 12, "sm": 6},
            bgcolor="#1A1A1C",
        )
        cat_field = ft.TextField(
            label="Catégorie",
            value=str(article.get("categorie", "Général")) if is_edit else "Général",
            col={"xs": 12, "sm": 6},
            bgcolor="#1A1A1C",
        )
        ht_field = ft.TextField(
            label="Prix HT (€)",
            value=str(article.get("prix_ht", "0.0")) if is_edit else "0.0",
            keyboard_type=ft.KeyboardType.NUMBER,
            col={"xs": 6, "sm": 3},
            bgcolor="#1A1A1C",
        )
        stock_field = ft.TextField(
            label="Stock actuel",
            value=str(article.get("stock", "0")) if is_edit else "0",
            keyboard_type=ft.KeyboardType.NUMBER,
            col={"xs": 6, "sm": 3},
            bgcolor="#1A1A1C",
        )

        def enregistrer(evt):
            try:
                raw_ht = (ht_field.value or "0").strip().replace(",", ".")
                p_ht = float(raw_ht) if raw_ht else 0.0

                raw_stk = (stock_field.value or "0").strip()
                stk = int(float(raw_stk)) if raw_stk else 0
            except ValueError:
                self._show_snackbar("Prix et stock doivent être des nombres valides.", is_error=True)
                return

            if not des_field.value or not des_field.value.strip():
                self._show_snackbar("La désignation est obligatoire.", is_error=True)
                return

            try:
                if not hasattr(self.app, "articles") or not isinstance(self.app.articles, list):
                    self.app.articles = []

                if is_edit:
                    article["reference"] = ref_field.value.strip()
                    article["designation"] = des_field.value.strip()
                    article["categorie"] = cat_field.value.strip()
                    article["prix_ht"] = p_ht
                    article["prix_ttc"] = round(p_ht * 1.2, 2)
                    article["stock"] = stk
                else:
                    nouvel_article = {
                        "id": len(self.app.articles) + 1,
                        "reference": ref_field.value.strip(),
                        "designation": des_field.value.strip(),
                        "categorie": cat_field.value.strip(),
                        "prix_ht": p_ht,
                        "prix_ttc": round(p_ht * 1.2, 2),
                        "stock": stk,
                    }
                    self.app.articles.append(nouvel_article)

                if hasattr(self.app, "save_data"):
                    self.app.save_data()

                self._fermer_dialogue(dlg)
                self.refresh_list(self.search_input.value or "")
                self._show_snackbar("Article enregistré avec succès !")
            except Exception as ex:
                print(f"Erreur enregistrer : {ex}")
                self._show_snackbar(f"Erreur d'enregistrement : {ex}", is_error=True)

        dlg = ft.AlertDialog(
            title=ft.Text("Modifier l'article" if is_edit else "Nouvel Article"),
            content=ft.Container(
                width=500,
                content=ft.ResponsiveRow([
                    ref_field,
                    des_field,
                    cat_field,
                    ht_field,
                    stock_field,
                ]),
            ),
            actions=[
                ft.TextButton(
                    content=ft.Text("Annuler"),
                    on_click=lambda evt: self._fermer_dialogue(dlg)
                ),
                ft.ElevatedButton(
                    content=ft.Text("Enregistrer"),
                    bgcolor=self.accent_color,
                    color="white",
                    on_click=enregistrer,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self._ouvrir_dialogue(dlg)

    def _ouvrir_dialogue(self, dlg):
        page_obj = self.get_page()
        if page_obj:
            try:
                page_obj.open(dlg)
            except Exception:
                dlg.open = True
                if dlg not in page_obj.overlay:
                    page_obj.overlay.append(dlg)
                page_obj.update()

    def _fermer_dialogue(self, dlg):
        page_obj = self.get_page()
        if page_obj:
            try:
                page_obj.close(dlg)
            except Exception:
                dlg.open = False
                page_obj.update()

    def supprimer_article(self, e, article):
        def confirmation_action(confirme):
            self._fermer_dialogue(dlg)
            if confirme:
                if hasattr(self.app, "articles") and isinstance(self.app.articles, list):
                    if article in self.app.articles:
                        self.app.articles.remove(article)
                        if hasattr(self.app, "save_data"):
                            self.app.save_data()
                        self.refresh_list(self.search_input.value or "")
                        self._show_snackbar("Article supprimé.")

        dlg = ft.AlertDialog(
            title=ft.Text("🚨 Suppression"),
            content=ft.Text(f"Voulez-vous vraiment supprimer l'article '{article.get('designation', '')}' ?"),
            actions=[
                ft.TextButton(
                    content=ft.Text("Annuler"),
                    on_click=lambda _: confirmation_action(False)
                ),
                ft.ElevatedButton(
                    content=ft.Text("Supprimer"),
                    bgcolor="#B91C1C",
                    color="white",
                    on_click=lambda _: confirmation_action(True)
                ),
            ],
        )
        self._ouvrir_dialogue(dlg)

    def _show_snackbar(self, message: str, is_error: bool = False):
        color = "#B91C1C" if is_error else "#15803D"
        page_obj = self.get_page()
        if page_obj:
            snack = ft.SnackBar(content=ft.Text(message), bgcolor=color)
            try:
                page_obj.open(snack)
            except Exception:
                page_obj.snack_bar = snack
                snack.open = True
                page_obj.update()
