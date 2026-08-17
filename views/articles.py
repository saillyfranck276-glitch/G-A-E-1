import flet as ft
from pathlib import Path

CARD_COLOR = "#1E1E22"
PRIMARY_COLOR = "#2B719E"
ERROR_COLOR = "#EF4444"

class ArticlesView(ft.Container):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.expand = True
        self.padding = 20
        
        # État interne
        self.editing_idx = None
        
        # Détection du statut TVA
        self.tva_applicable = self.detecter_statut_tva()
        
        # 🛡️ SOURCE DE DONNÉES CENTRALISÉE (Alignée avec main.py)
        if not hasattr(self.app, "articles"):
            self.app.articles = []
        
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
        """Appelé automatiquement par Flet quand le contrôle est ajouté à la page."""
        self.refresh_list()

    def _build_interface(self):
        # --- FORMULAIRE (Gauche) ---
        self.fields = {
            "ref": ft.TextField(label="Référence / SKU", bgcolor="#242426"),
            "designation": ft.TextField(label="Désignation", bgcolor="#242426"),
            "categorie": ft.TextField(label="Catégorie", bgcolor="#242426"),
            "prix_ht": ft.TextField(label="Prix Unitaire HT", bgcolor="#242426"),
            "stock": ft.TextField(label="Stock", bgcolor="#242426")
        }
        
        self.tf_tva = ft.TextField(
            label="Taux TVA (%)", 
            value="20" if self.tva_applicable else "0", 
            bgcolor="#242426", 
            disabled=not self.tva_applicable
        )
        
        self.lbl_status = ft.Text("", size=12)

        form_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
        for field in self.fields.values():
            form_column.controls.append(field)
        form_column.controls.append(self.tf_tva)
        
        self.btn_save = ft.ElevatedButton(
            "💾 Enregistrer l'Article", 
            on_click=self.valider_article, 
            bgcolor=PRIMARY_COLOR, 
            color="white"
        )
        form_column.controls.append(self.btn_save)
        form_column.controls.append(self.lbl_status)

        # --- LISTE (Droite) ---
        self.search_entry = ft.TextField(
            hint_text="🔍 Rechercher un article...", 
            on_change=lambda _: self.refresh_list(), 
            bgcolor="#1A1A1C"
        )
        self.list_container = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
        
        self.content = ft.Row([
            ft.Container(content=form_column, width=320, bgcolor=CARD_COLOR, padding=20, border_radius=12),
            ft.Container(content=ft.Column([self.search_entry, self.list_container]), expand=True, padding=20)
        ], vertical_alignment=ft.CrossAxisAlignment.START, expand=True)

    def refresh_list(self):
        """Regénère l'affichage de la liste."""
        self.list_container.controls.clear()
        search = self.search_entry.value.lower() if self.search_entry.value else ""
        
        for idx, art in enumerate(self.app.articles):
            designation = art.get("designation", "")
            if search and search not in designation.lower():
                continue
                
            card = ft.Container(
                content=ft.Row([
                    ft.Column([
                        ft.Text(designation, weight=ft.FontWeight.BOLD, color="#38BDF8"),
                        ft.Text(f"Réf: {art.get('ref', '')} | Prix: {art.get('prix_ht', 0)}€ HT | Stock: {art.get('stock', 0)}", size=12, color="grey")
                    ], expand=True),
                    ft.IconButton(ft.Icons.EDIT, on_click=lambda e, i=idx, a=art: self.charger_article(i, a)),
                    ft.IconButton(ft.Icons.DELETE, on_click=lambda e, i=idx: self.supprimer_article(i), icon_color=ERROR_COLOR)
                ]),
                bgcolor=CARD_COLOR,
                padding=15,
                border_radius=8,
                margin=ft.margin.only(bottom=10)
            )
            self.list_container.controls.append(card)
        
        if self.page:
            self.update()

    def charger_article(self, idx, article):
        self.editing_idx = idx
        for key, field in self.fields.items():
            field.value = str(article.get(key, ""))
        self.tf_tva.value = str(article.get("tva", "0"))
        self.update()

    def vider_champs(self):
        self.editing_idx = None
        for field in self.fields.values(): 
            field.value = ""
        self.tf_tva.value = "20" if self.tva_applicable else "0"
        self.lbl_status.value = ""
        self.update()

    def valider_article(self, e):
        # 1. Conversion et vérification numérique
        try:
            raw_prix = self.fields["prix_ht"].value or "0"
            raw_tva = self.tf_tva.value or "0"
            raw_stock = self.fields["stock"].value or "0"

            prix_ht = float(raw_prix.replace(",", "."))
            tva = float(raw_tva.replace(",", ".")) if self.tva_applicable else 0.0
            stock = int(raw_stock)
        except (ValueError, AttributeError, TypeError):
            self.lbl_status.value = "Erreur : Vérifiez les valeurs numériques (Prix, Stock)."
            self.lbl_status.color = ERROR_COLOR
            self.update()
            return

        # 2. Construction du dictionnaire
        data = {}
        for k, f in self.fields.items():
            data[k] = f.value.strip() if f.value else ""
            
        data["prix_ht"] = prix_ht
        data["tva"] = tva
        data["stock"] = stock

        # 3. Sauvegarde dans la liste globale
        if self.editing_idx is not None:
            self.app.articles[self.editing_idx].update(data)
        else:
            self.app.articles.append(data)
            
        # 4. Écriture physique sur le disque
        if hasattr(self.app, "save_data"):
            self.app.save_data()
            
        self.refresh_list()
        self.vider_champs()

    def supprimer_article(self, idx):
        self.app.articles.pop(idx)
            
        if hasattr(self.app, "save_data"):
            self.app.save_data()
            
        self.refresh_list()