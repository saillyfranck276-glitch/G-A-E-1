import flet as ft


def get_icon(name: str):
  """Assistant universel d'icônes compatible Android et Desktop."""
  name_upper = name.upper()
  if hasattr(ft, "Icons") and hasattr(ft.Icons, name_upper):
    return getattr(ft.Icons, name_upper)
  if hasattr(ft, "icons") and hasattr(ft.icons, name_upper):
    return getattr(ft.icons, name_upper)
  return name.lower()


def safe_border(width=1, color="grey800"):
  """Bordure universelle pour éviter 'ft.border.all' sur APK Android."""
  side = ft.BorderSide(width, color)
  return ft.Border(top=side, right=side, bottom=side, left=side)


class ArticlesView(ft.Container):

  def __init__(self, app):
    super().__init__(expand=True)
    self.app = app

    # Couleurs de thème de l'entreprise
    self.entreprise_data = getattr(
        self.app, "entreprise", getattr(self.app, "association", {})
    )
    self.accent_color = self.entreprise_data.get("accent_color", "#2B719E")

    # Champ de recherche et bouton d'ajout
    self.search_input = ft.TextField(
        hint_text="Rechercher par désignation ou référence...",
        prefix_icon=get_icon("SEARCH"),
        on_change=self.on_search_change,
        expand=True,
    )

    self.btn_add = ft.ElevatedButton(
        "Nouveau Produit / Article",
        icon=get_icon("ADD"),
        bgcolor=self.accent_color,
        color="white",
        on_click=lambda e: self.ouvrir_dialogue_article(),
    )

    # Conteneur scrollable de la liste d'articles
    self.list_container = ft.Column(spacing=10, scroll="auto", expand=True)

    self.content = ft.Container(
        padding=15,
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            "📦 Gestion des Articles & Stock",
                            size=18,
                            weight="bold",
                            expand=True,
                        ),
                        self.btn_add,
                    ],
                    alignment="spaceBetween",
                ),
                ft.Row([self.search_input]),
                ft.Divider(color="grey800"),
                self.list_container,
            ],
            spacing=12,
            expand=True,
        ),
    )

  def safe_update(self):
    """Mise à jour sécurisée de l'UI."""
    try:
      if self.page:
        self.update()
    except Exception:
      pass

  def did_mount(self):
    """Initialisation au chargement de la vue."""
    self.refresh_list()

  def refresh_list(self, filter_text=""):
    """Rafraîchit la liste des articles affichés."""
    self.list_container.controls.clear()
    articles = getattr(self.app, "articles", [])

    query = filter_text.lower().strip()

    filtered_articles = [
        a
        for a in articles
        if query in a.get("designation", "").lower()
        or query in a.get("reference", "").lower()
        or query in a.get("categorie", "").lower()
    ]

    if not filtered_articles:
      self.list_container.controls.append(
          ft.Container(
              padding=20,
              alignment=ft.alignment.center,
              content=ft.Text(
                  "Aucun article disponible.", color="grey400", italic=True
              ),
          )
      )
      self.safe_update()
      return

    for article in filtered_articles:
      card = self._build_article_card(article)
      self.list_container.controls.append(card)

    self.safe_update()

  def _build_article_card(self, article):
    """Construit une carte d'article compatible Android (sans ft.border.all)."""
    ref = article.get("reference", "N/A")
    designation = article.get("designation", "Sans nom")
    categorie = article.get("categorie", "Général")
    prix_ht = article.get("prix_ht", 0.0)
    prix_ttc = article.get("prix_ttc", round(prix_ht * 1.2, 2))
    stock = article.get("stock", 0)

    stock_color = (
        "green400" if stock > 5 else ("orange400" if stock > 0 else "red400")
    )

    return ft.Container(
        padding=12,
        bgcolor="#1e293b",
        border_radius=8,
        border=safe_border(1, "grey800"),  # ✅ Compatible Android
        content=ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(f"{designation}", weight="bold", size=15),
                        ft.Text(
                            f"Réf: {ref} | Catégorie: {categorie}",
                            size=12,
                            color="grey400",
                        ),
                    ],
                    expand=True,
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
                        ft.Text(f"({prix_ht:.2f} € HT)", size=11, color="grey400"),
                    ],
                    alignment="center",
                    horizontal_alignment="end",
                    spacing=2,
                ),
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
                ft.Row(
                    [
                        ft.IconButton(
                            icon=get_icon("EDIT"),
                            icon_size=18,
                            tooltip="Modifier",
                            on_click=lambda e,
                            a=article: self.ouvrir_dialogue_article(a),
                        ),
                        ft.IconButton(
                            icon=get_icon("DELETE"),
                            icon_size=18,
                            icon_color="red400",
                            tooltip="Supprimer",
                            on_click=lambda e,
                            a=article: self.supprimer_article(a),
                        ),
                    ],
                    spacing=0,
                ),
            ],
            alignment="spaceBetween",
            vertical_alignment="center",
        ),
    )

  def on_search_change(self, e):
    self.refresh_list(self.search_input.value or "")

  def ouvrir_dialogue_article(self, article=None):
    is_edit = article is not None

    ref_field = ft.TextField(
        label="Référence",
        value=article.get("reference", "") if is_edit else "",
        col={"sm": 12, "md": 6},
    )
    des_field = ft.TextField(
        label="Désignation",
        value=article.get("designation", "") if is_edit else "",
        col={"sm": 12, "md": 6},
    )
    cat_field = ft.TextField(
        label="Catégorie",
        value=article.get("categorie", "Général") if is_edit else "Général",
        col={"sm": 12, "md": 6},
    )
    ht_field = ft.TextField(
        label="Prix HT (€)",
        value=str(article.get("prix_ht", "")) if is_edit else "0.0",
        keyboard_type="number",
        col={"sm": 6, "md": 3},
    )
    stock_field = ft.TextField(
        label="Stock actuel",
        value=str(article.get("stock", "")) if is_edit else "0",
        keyboard_type="number",
        col={"sm": 6, "md": 3},
    )

    def enregistrer(e):
      try:
        p_ht = float((ht_field.value or "0").replace(",", "."))
        stk = int(stock_field.value or "0")
      except ValueError:
        self._show_snackbar(
            "Prix et stock doivent être des nombres valides.", is_error=True
        )
        return

      if not des_field.value.strip():
        self._show_snackbar(
            "La désignation est obligatoire.", is_error=True
        )
        return

      if not hasattr(self.app, "articles"):
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
              "Annuler", on_click=lambda e: self._fermer_dialogue(dlg)
          ),
          ft.ElevatedButton(
              "Enregistrer",
              bgcolor=self.accent_color,
              color="white",
              on_click=enregistrer,
          ),
      ],
        actions_alignment="end",
    )

    page_obj = getattr(self.app, "page", None) or self.page
    if page_obj:
      if hasattr(page_obj, "open"):
        page_obj.open(dlg)
      else:
        page_obj.dialog = dlg
        dlg.open = True
        page_obj.update()

  def _fermer_dialogue(self, dlg):
    page_obj = getattr(self.app, "page", None) or self.page
    if page_obj and hasattr(page_obj, "close"):
      page_obj.close(dlg)
    else:
      dlg.open = False
    self.safe_update()

  def supprimer_article(self, article):
    if hasattr(self.app, "articles") and article in self.app.articles:
      self.app.articles.remove(article)
      if hasattr(self.app, "save_data"):
        self.app.save_data()
      self.refresh_list(self.search_input.value or "")
      self._show_snackbar("Article supprimé.")

  def _show_snackbar(self, message: str, is_error: bool = False):
    color = "red700" if is_error else "green700"
    page_obj = getattr(self.app, "page", None) or self.page
    if page_obj:
      snack = ft.SnackBar(ft.Text(message), bgcolor=color)
      if hasattr(page_obj, "open"):
        try:
          page_obj.open(snack)
        except Exception:
          page_obj.snack_bar = snack
          snack.open = True
      else:
        page_obj.snack_bar = snack
        snack.open = True
      self.safe_update()
