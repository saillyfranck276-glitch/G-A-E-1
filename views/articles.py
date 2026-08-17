import flet as ft

CARD_COLOR = "#1E1E22"
PRIMARY_COLOR = "#2B719E"
ERROR_COLOR = "#EF4444"

class ArticlesView(ft.Container):
    """Vue Flet pour la gestion des articles (100% Mobile & Desktop)."""

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.expand = True
        self.padding = 10
        
        # État interne
        self.editing_idx = None
        self.tva_applicable = self.detecter_statut_tva()
        
        # Source de données centralisée
        if not hasattr(self.app, "articles"):
            self.app.articles = []

        self.main_layout = ft.Container(expand=True)
        self._build_interface()

    def detecter_statut_tva(self):
        """Vérifie si la TVA est activée dans la configuration entreprise."""
        if hasattr(self.app, "entreprise") and isinstance(self.app.entreprise, dict):
            tva = self.app.entreprise.get("tva_activee", False)
            if isinstance(tva, bool):
                return tva
            return str(tva).lower() in ["true", "1", "oui"]
        return False

    def did_mount(self):
        """Détecte le redimensionnement et charge la liste au montage."""
        if self.page:
            self.page.on_resized = self._on_screen_resize
        self.refresh_list()

    def _is_mobile(self):
        return self.page.width < 768 if self.page else False

    def _on_screen_resize(self, e):
        self.refresh_list()

    def _build_interface(self):
        # Champs du formulaire
        self.fields = {
            "ref": ft.TextField(label="Référence / SKU", bgcolor="#242426", text_size=13),
            "designation": ft.TextField(label="Désignation *", bgcolor="#242426", text_size=13),
            "categorie": ft.TextField(label="Catégorie", bgcolor="#242426", text_size=13),
            "prix_ht": ft.TextField(label="Prix Unitaire HT (€)", bgcolor="#242426", text_size=13),
            "stock": ft.TextField(label="Stock", bgcolor="#242426", text_size=13)
        }
        
        self.tf_tva = ft.TextField(
            label="Taux TVA (%)", 
            value="20" if self.tva_applicable else "0", 
            bgcolor="#242426", 
            disabled=not self.tva_applicable,
            text_size=13
        )
        
        self.form_title = ft.Text("➕ Ajouter un article", size=16, weight=ft.FontWeight.BOLD)

        self.btn_save = ft.ElevatedButton(
            "💾 Enregistrer", 
            on_click=self.valider_article, 
            bgcolor=PRIMARY_COLOR, 
            color="white"
        )
        
        self.btn_reset = ft.OutlinedButton(
            "❌ Annuler", 
            on_click=lambda e: self.vider_champs(),
            style=ft.ButtonStyle(color="white")
        )

        # Barre de recherche
        self.search_entry = ft.TextField(
            hint_text="🔍 Rechercher (désignation, réf, catégorie)...", 
            on_change=lambda _: self.refresh_list(), 
            bgcolor="#1A1A1C",
            text_size=13,
            expand=True
        )
        
        self.list_container = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)

        # Structure principale
        header = ft.Row([
            ft.IconButton("arrow_back_rounded", on_click=lambda e: self.app.navigate_to("Dashboard")),
            ft.Text("📦 Gestion des Articles", size=20, weight=ft.FontWeight.BOLD)
        ])

        self.content = ft.Column(
            controls=[header, self.main_layout],
            expand=True,
            spacing=10
        )

    def refresh_list(self, e=None):
        """Regénère dynamiquement la liste et la disposition responsive."""
        self.list_container.controls.clear()
        search = self.search_entry.value.lower().strip() if self.search_entry.value else ""
        
        for idx, art in enumerate(getattr(self.app, "articles", [])):
            designation = str(art.get("designation", ""))
            ref = str(art.get("ref", ""))
            cat = str(art.get("categorie", ""))
            
            if search and not (search in designation.lower() or search in ref.lower() or search in cat.lower()):
                continue
                
            card = ft.Container(
                content=ft.Row([
                    ft.Column([
                        ft.Text(designation or "Sans nom", weight=ft.FontWeight.BOLD, color="#38BDF8", size=14),
                        ft.Text(f"Réf: {ref or 'N/A'} | Cat: {cat or 'N/A'}", size=12, color="#AEAEB2"),
                        ft.Text(f"Prix HT: {float(art.get('prix_ht', 0)):.2f}€ | TVA: {art.get('tva', 0)}% | Stock: {art.get('stock', 0)}", size=12, color="#E5E7EB")
                    ], expand=True, spacing=3),
                    ft.Row([
                        ft.IconButton(ft.Icons.EDIT, icon_size=18, on_click=lambda e, i=idx, a=art: self.charger_article(i, a)),
                        ft.IconButton(ft.Icons.DELETE, icon_size=18, on_click=lambda e, i=idx: self.supprimer_article(i), icon_color=ERROR_COLOR)
                    ], spacing=0)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                bgcolor=CARD_COLOR,
                padding=12,
                border_radius=8,
                border=ft.border.all(1, "#2A2A32")
            )
            self.list_container.controls.append(card)

        if not self.list_container.controls:
            self.list_container.controls.append(
                ft.Text("Aucun article trouvé.", color="#AEAEB2", size=13)
            )

        # Construction des conteneurs Réactifs
        form_card = ft.Container(
            content=ft.Column(
                controls=[
                    self.form_title,
                    *[f for f in self.fields.values()],
                    self.tf_tva,
                    ft.Row([self.btn_save, self.btn_reset], spacing=10)
                ],
                spacing=8,
                scroll=ft.ScrollMode.AUTO
            ),
            bgcolor=CARD_COLOR,
            padding=15,
            border_radius=12,
            border=ft.border.all(1, "#2A2A32")
        )

        list_card = ft.Container(
            content=ft.Column([
                ft.Row([self.search_entry]),
                self.list_container
            ], expand=True, spacing=10),
            expand=True
        )

        # Disposition conditionnelle selon la taille de l'écran
        if self._is_mobile():
            self.main_layout.content = ft.Column(
                controls=[form_card, list_card],
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                spacing=15
            )
        else:
            form_card.width = 340
            self.main_layout.content = ft.Row(
                controls=[form_card, list_card],
                vertical_alignment=ft.CrossAxisAlignment.START,
                expand=True,
                spacing=15
            )

        if self.page:
            self.update()

    def charger_article(self, idx, article):
        """Passe en mode édition et remplit le formulaire."""
        self.editing_idx = idx
        self.form_title.value = f"✏️ Modifier l'article #{idx + 1}"
        for key, field in self.fields.items():
            field.value = str(article.get(key, ""))
        self.tf_tva.value = str(article.get("tva", "20" if self.tva_applicable else "0"))
        self.refresh_list()

    def vider_champs(self):
        """Réinitialise le formulaire."""
        self.editing_idx = None
        self.form_title.value = "➕ Ajouter un article"
        for field in self.fields.values(): 
            field.value = ""
        self.tf_tva.value = "20" if self.tva_applicable else "0"
        self.refresh_list()

    def valider_article(self, e):
        """Valide et enregistre un article."""
        if not self.fields["designation"].value or not self.fields["designation"].value.strip():
            self.show_snack("La désignation est obligatoire.", is_error=True)
            return

        try:
            raw_prix = self.fields["prix_ht"].value or "0"
            raw_tva = self.tf_tva.value or "0"
            raw_stock = self.fields["stock"].value or "0"

            prix_ht = float(raw_prix.replace(",", "."))
            tva = float(raw_tva.replace(",", ".")) if self.tva_applicable else 0.0
            stock = int(raw_stock)
        except (ValueError, AttributeError, TypeError):
            self.show_snack("Erreur : Vérifiez les valeurs numériques (Prix, Stock, TVA).", is_error=True)
            return

        data = {k: f.value.strip() for k, f in self.fields.items()}
        data["prix_ht"] = prix_ht
        data["tva"] = tva
        data["stock"] = stock

        if self.editing_idx is not None:
            self.app.articles[self.editing_idx].update(data)
            self.show_snack("Article mis à jour avec succès !")
        else:
            self.app.articles.append(data)
            self.show_snack("Article ajouté avec succès !")
            
        if hasattr(self.app, "save_data"):
            self.app.save_data()
            
        self.vider_champs()

    def supprimer_article(self, idx):
        """Supprime l'article sélectionné."""
        if 0 <= idx < len(self.app.articles):
            self.app.articles.pop(idx)
            if hasattr(self.app, "save_data"):
                self.app.save_data()
            self.show_snack("Article supprimé.")
            self.refresh_list()

    def show_snack(self, message, is_error=False):
        """Affiche une notification en bas d'écran."""
        if self.page:
            self.page.snack_bar = ft.SnackBar(
                content=ft.Text(message), 
                bgcolor=ERROR_COLOR if is_error else "green"
            )
            self.page.snack_bar.open = True
            self.page.update()
