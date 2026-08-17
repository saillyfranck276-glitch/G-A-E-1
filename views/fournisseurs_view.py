import os
import shutil
from pathlib import Path
import flet as ft


class FournisseursView(ft.Column):

  def __init__(self, app):
    super().__init__(expand=True, spacing=10)
    self.app = app

    # Récupération sécurisée de la couleur d'accentuation
    entreprise = getattr(self.app, "entreprise", {}) or {}
    self.accent_color = entreprise.get("accent_color", "#2B719E")

    # États de suivi de l'interface
    self.editing_idx = None
    self.opened_docs_idx = None
    self.selected_row_data = None

    # Contexte temporaire pour l'import de pièces jointes PDF
    self.current_upload_fournisseur = None
    self.current_upload_idx = None
    self.current_upload_category = None

    # Sélecteur de fichiers natif (rattaché dans did_mount)
    self.file_picker = ft.FilePicker(on_result=self.on_file_picker_result)

    self.setup_ui()

  def did_mount(self):
    """Cycle de vie Flet : attachement sécurisé du FilePicker à l'overlay de la page."""
    if self.page and self.file_picker not in self.page.overlay:
      self.page.overlay.append(self.file_picker)
      self.page.update()

  def setup_ui(self):
    """Crée l'en-tête et les onglets segmentés."""
    # En-tête principal
    self.controls.append(
        ft.Row(
            controls=[
                ft.Text(
                    "📦 Chaîne Logistique : Fournisseurs & Achats",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                )
            ],
            alignment=ft.MainAxisAlignment.START,
        )
    )

    # Système d'onglets segmentés
    self.tab_view = ft.SegmentedButton(
        segments=[
            ft.Segment(
                value="repertoire",
                label=ft.Text("🏢 Répertoire Fournisseurs", size=12),
            ),
            ft.Segment(
                value="achats",
                label=ft.Text("📄 Suivi des Achats (BC / BL)", size=12),
            ),
        ],
        selected={"repertoire"},
        on_change=self._toggle_tabs,
    )
    self.controls.append(self.tab_view)

    # Zone d'affichage dynamique principale
    self.main_container = ft.Container(expand=True)
    self.controls.append(self.main_container)

    # Rendu initial du répertoire
    self._afficher_fournisseurs()

  def _toggle_tabs(self, e):
    """Bascule l'affichage entre le répertoire et le tableau des achats."""
    choix = next(iter(self.tab_view.selected))
    if choix == "repertoire":
      self._afficher_fournisseurs()
    else:
      self._afficher_documents_achat()
    if self.page:
      self.page.update()

  # ─────────────────────────────────────────────────────────────────────────
  # 🏢 COMPOSANT 1 : RÉPERTOIRE FOURNISSEURS (Design Split-View)
  # ─────────────────────────────────────────────────────────────────────────
  def _afficher_fournisseurs(self):
    self.entries = {}

    # --- COLONNE GAUCHE : FORMULAIRE DES COORDONNÉES ---
    fields_config = [
        ("nom", "Nom du Fournisseur *", "Ex: Grossiste ACME..."),
        ("contact_nom", "Contact Commercial", "Ex: Marc Durand"),
        ("email", "E-mail Commercial", "Ex: commandes@fournisseur.com"),
        ("telephone", "Téléphone", "Ex: 01 23 45 67 89"),
        ("adresse", "Adresse Siège", "Ex: 45 Avenue de la République"),
        ("code_postal", "Code Postal", "Ex: 69000"),
        ("ville", "Ville", "Ex: Lyon"),
        ("siret", "Numéro SIRET", "Ex: 987 654 321 00015"),
        ("iban", "IBAN / RIB", "Ex: FR76 3000 1000 ..."),
        ("delai_paiement", "Délai de paiement", "Ex: 30 jours fin de mois"),
    ]

    form_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)
    self.lbl_form_title = ft.Text(
        "📝 Ajouter un nouveau partenaire",
        size=14,
        weight=ft.FontWeight.BOLD,
        color=self.accent_color,
    )
    form_column.controls.append(self.lbl_form_title)

    for key, label, placeholder in fields_config:
      form_column.controls.append(
          ft.Text(label, size=11, weight=ft.FontWeight.BOLD, color="#AEAEB2")
      )
      tf = ft.TextField(
          hint_text=placeholder,
          bgcolor="#242426",
          border_color="#2A2A2E",
          height=36,
          text_size=12,
          content_padding=10,
      )
      self.entries[key] = tf
      form_column.controls.append(tf)

    self.lbl_status = ft.Text("", size=11, italic=True, color="red400")
    form_column.controls.append(self.lbl_status)

    self.btn_save = ft.ElevatedButton(
        "💾 Enregistrer le Fournisseur",
        bgcolor="#15803D",
        color="white",
        width=340,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
        on_click=self._valider_fournisseur,
    )
    form_column.controls.append(self.btn_save)

    self.btn_cancel = ft.OutlinedButton(
        "🔄 Annuler / Vider",
        width=340,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
        on_click=self.vider_champs,
    )
    form_column.controls.append(self.btn_cancel)

    left_frame = ft.Container(
        content=form_column,
        width=360,
        bgcolor="#1A1A1C",
        border_radius=12,
        padding=15,
    )

    # --- COLONNE DROITE : LISTE DES FOURNISSEURS + RECHERCHE ---
    self.search_entry = ft.TextField(
        hint_text="🔍 Rechercher un fournisseur par nom, contact ou email...",
        bgcolor="#1A1A1C",
        height=40,
        text_size=12,
        content_padding=10,
        on_change=self.refresh_fournisseur_list,
    )

    self.list_column = ft.Column(
        scroll=ft.ScrollMode.AUTO, expand=True, spacing=10
    )

    count_fourn = len(getattr(self.app, "fournisseurs", []))
    self.list_title = ft.Text(
        f"Fiches partenaires enregistrées ({count_fourn})",
        size=13,
        weight=ft.FontWeight.BOLD,
        color="#AEAEB2",
    )

    right_frame = ft.Column(
        controls=[
            self.search_entry,
            self.list_title,
            ft.Container(
                content=self.list_column,
                expand=True,
                bgcolor="#141416",
                border_radius=8,
                padding=10,
            ),
        ],
        expand=True,
    )

    # Organisation globale en ligne
    self.main_container.content = ft.Row(
        controls=[left_frame, right_frame],
        expand=True,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )

    self.refresh_fournisseur_list(None)

  def refresh_fournisseur_list(self, e):
    """Régénère la liste filtrée."""
    search_term = (
        self.search_entry.value.lower().strip() if self.search_entry.value else ""
    )
    self.list_column.controls.clear()

    fournisseurs = getattr(self.app, "fournisseurs", [])

    if not fournisseurs:
      self.list_column.controls.append(
          ft.Text(
              "Aucun fournisseur dans votre base de données.",
              size=13,
              italic=True,
              color="#636366",
          )
      )
      if self.page:
        self.page.update()
      return

    visible_fourn = 0

    for idx, f in enumerate(fournisseurs):
      nom = f.get("nom", "").lower()
      contact = f.get("contact_nom", "").lower()
      tel = f.get("telephone", "").lower()
      email = f.get("email", "").lower()

      if search_term and not (
          search_term in nom
          or search_term in contact
          or search_term in tel
          or search_term in email
      ):
        continue

      visible_fourn += 1

      if "documents_externes" not in f or not isinstance(
          f["documents_externes"], list
      ):
        f["documents_externes"] = []

      # Texte des coordonnées descriptives
      details_text = (
          f"👤 Contact : {f.get('contact_nom') or 'Non renseigné'}   |   📞"
          f" {f.get('telephone') or 'Non renseigné'}\n✉️"
          f" {f.get('email') or 'Non renseigné'}   |   📍"
          f" {f.get('adresse') or '-'} {f.get('code_postal') or ''}"
          f" {f.get('ville') or ''}"
      )

      # Gestion du sous-panneau dépliable pour les pièces jointes
      docs_panel = ft.Column(visible=(self.opened_docs_idx == idx), spacing=5)
      if self.opened_docs_idx == idx:
        self.populate_docs_panel(docs_panel, f, idx)

      # Rendu de la carte fournisseur
      card_content = ft.Column(
          controls=[
              ft.Row(
                  controls=[
                      ft.Column(
                          controls=[
                              ft.Text(
                                  f["nom"].upper(),
                                  size=13,
                                  weight=ft.FontWeight.BOLD,
                                  color="#38BDF8",
                              ),
                              ft.Text(details_text, size=11, color="#E5E7EB"),
                          ],
                          expand=True,
                      ),
                      ft.Column(
                          controls=[
                              ft.ElevatedButton(
                                  "✏️ Modifier",
                                  bgcolor=self.accent_color,
                                  color="white",
                                  height=28,
                                  text_size=11,
                                  on_click=lambda e, i=idx, item=f: self.charger_fournisseur(
                                      i, item
                                  ),
                              ),
                              ft.ElevatedButton(
                                  "👁️ Fiche",
                                  bgcolor="#6B7280",
                                  color="white",
                                  height=28,
                                  text_size=11,
                                  on_click=lambda e, item=f: self._voir_fiche_interne(
                                      item
                                  ),
                              ),
                              ft.ElevatedButton(
                                  f"📁 Docs ({len(f['documents_externes'])})",
                                  bgcolor="#10B981",
                                  color="white",
                                  height=28,
                                  text_size=11,
                                  on_click=lambda e, i=idx: self.toggle_documents_panel(
                                      i
                                  ),
                              ),
                              ft.ElevatedButton(
                                  "🗑️ Supprimer",
                                  bgcolor="#991B1B",
                                  color="white",
                                  height=28,
                                  text_size=11,
                                  on_click=lambda e, item=f: self._supprimer_fournisseur(
                                      item
                                  ),
                              ),
                          ],
                          alignment=ft.MainAxisAlignment.CENTER,
                          spacing=4,
                      ),
                  ],
                  alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
              ),
              docs_panel,
          ],
          spacing=10,
      )

      card = ft.Container(
          content=card_content,
          bgcolor="#242426",
          border=ft.border.all(1, "#3A3A3C"),
          border_radius=8,
          padding=12,
      )
      self.list_column.controls.append(card)

    if visible_fourn == 0 and search_term:
      self.list_column.controls.append(
          ft.Text(
              "🔍 Aucun fournisseur ne correspond à votre recherche.",
              size=12,
              italic=True,
              color="#636366",
          )
      )

    self.list_title.value = (
        f"Fiches partenaires enregistrées ({len(fournisseurs)})"
    )
    if self.page:
      self.page.update()

  # ─────────────────────────────────────────────────────────────────────────
  # 📁 VOLET DES PIÈCES JOINTES
  # ─────────────────────────────────────────────────────────────────────────
  def toggle_documents_panel(self, idx):
    self.opened_docs_idx = None if self.opened_docs_idx == idx else idx
    self.refresh_fournisseur_list(None)

  def populate_docs_panel(self, container_col, fournisseur, fourn_idx):
    """Construit le volet de pièces jointes sous le fournisseur."""
    categories = [
        "RIB / Banque",
        "Contrat Commercial",
        "Extrait Kbis",
        "Devis Référence",
        "Autre Document",
    ]
    cat_combo = ft.Dropdown(
        options=[ft.dropdown.Option(c) for c in categories],
        value="RIB / Banque",
        height=36,
        text_size=12,
        content_padding=5,
        expand=True,
    )

    btn_add = ft.ElevatedButton(
        "➕ Ajouter un PDF",
        bgcolor="#2B719E",
        color="white",
        height=32,
        text_size=11,
        on_click=lambda e: self.declencher_ajout_pdf(
            fournisseur, fourn_idx, cat_combo.value
        ),
    )

    tools_row = ft.Row(
        controls=[
            ft.Text("Catégorie :", size=11, color="#AEAEB2"),
            cat_combo,
            btn_add,
        ],
        spacing=8,
    )

    rows_col = ft.Column(spacing=4)

    if not fournisseur["documents_externes"]:
      rows_col.controls.append(
          ft.Text(
              "Aucun document rattaché à ce fournisseur.",
              size=11,
              italic=True,
              color="#636366",
          )
      )
    else:
      for doc_idx, doc in enumerate(fournisseur["documents_externes"]):
        colors = {
            "RIB / Banque": "#3B82F6",
            "Contrat Commercial": "#10B981",
            "Extrait Kbis": "#F59E0B",
            "Devis Référence": "#8B5CF6",
        }
        bg_color = colors.get(doc["type"], "#6B7280")

        badge = ft.Container(
            content=ft.Text(
                f" {doc['type'].upper()} ",
                size=9,
                weight=ft.FontWeight.BOLD,
                color="white",
            ),
            bgcolor=bg_color,
            border_radius=4,
            padding=3,
        )

        row = ft.Row(
            controls=[
                badge,
                ft.Text(
                    doc["nom_fichier"], size=11, color="#E5E7EB", expand=True
                ),
                ft.IconButton(
                    ft.icons.REMOVE_RED_EYE_OUTLINED,
                    icon_size=16,
                    icon_color="#E5E7EB",
                    on_click=lambda e, d=doc: self.ouvrir_pdf(d),
                ),
                ft.IconButton(
                    ft.icons.DELETE_OUTLINE,
                    icon_size=16,
                    icon_color="red400",
                    on_click=lambda e, fourn=fournisseur, fi=fourn_idx, di=doc_idx: self.supprimer_pdf_fournisseur(
                        fourn, fi, di
                    ),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        rows_col.controls.append(row)

    container_col.controls.extend([
        ft.Divider(height=1, color="#48484A"),
        ft.Text(
            "📁 Pièces jointes & Classement PDF Fournisseur",
            size=11,
            weight=ft.FontWeight.BOLD,
            color="#A7F3D0",
        ),
        tools_row,
        rows_col,
    ])

  def declencher_ajout_pdf(self, fournisseur, fourn_idx, categorie):
    self.current_upload_fournisseur = fournisseur
    self.current_upload_idx = fourn_idx
    self.current_upload_category = categorie
    self.file_picker.pick_files(allowed_extensions=["pdf"])

  def on_file_picker_result(self, e: ft.FilePickerResultEvent):
    """Gère physiquement la copie du fichier PDF sélectionné sur le disque."""
    if not e.files or self.current_upload_fournisseur is None:
      return

    filepath = e.files[0].path
    if not filepath:
      return

    try:
      source = Path(filepath)
      base_dir = (
          Path(getattr(self.app, "data_dir", "data")) / "documents_fournisseurs"
      )

      nom_propre = (
          "".join(
              c
              for c in self.current_upload_fournisseur.get("nom", "Inconnu")
              if c.isalnum() or c in (" ", "_", "-")
          )
          .strip()
          .replace(" ", "_")
      )
      fourn_dir = base_dir / nom_propre
      fourn_dir.mkdir(parents=True, exist_ok=True)

      dest_file = fourn_dir / source.name
      compteur = 1
      while dest_file.exists():
        dest_file = fourn_dir / f"{source.stem}_{compteur}{source.suffix}"
        compteur += 1

      shutil.copy(str(source), str(dest_file))

      try:
        chemin_relatif = str(
            dest_file.relative_to(Path(getattr(self.app, "data_dir", ".")))
        )
      except ValueError:
        chemin_relatif = str(dest_file)

      self.current_upload_fournisseur["documents_externes"].append({
          "nom_fichier": dest_file.name,
          "type": self.current_upload_category,
          "chemin": chemin_relatif,
      })

      if hasattr(self.app, "save_data"):
        self.app.save_data()
      self.refresh_fournisseur_list(None)

    except Exception as ex:
      self.show_error_message(
          "Erreur d'importation", f"Impossible d'importer le document :\n{ex}"
      )
    finally:
      self.current_upload_fournisseur = None

  def supprimer_pdf_fournisseur(self, fournisseur, fourn_idx, doc_idx):
    doc = fournisseur["documents_externes"][doc_idx]

    def confirm():
      try:
        base_dir = Path(getattr(self.app, "data_dir", "."))
        file_path = base_dir / doc["chemin"]
        if file_path.exists():
          os.remove(file_path)

        fournisseur["documents_externes"].pop(doc_idx)
        if hasattr(self.app, "save_data"):
          self.app.save_data()
        self.refresh_fournisseur_list(None)
      except Exception as e:
        self.show_error_message(
            "Erreur de suppression", f"Une erreur est survenue :\n{e}"
        )

    self.show_confirm_dialog(
        "Confirmation",
        (
            "Voulez-vous vraiment détruire et détacher le document"
            f" '{doc['nom_fichier']}' ?"
        ),
        confirm,
    )

  def ouvrir_pdf(self, doc):
    try:
      base_dir = Path(getattr(self.app, "data_dir", "."))
      file_path = base_dir / doc["chemin"]
      if file_path.exists():
        self.app.pdf_file_path = str(file_path)
        self.app.navigate_to("PDFViewer", pdf_path=str(file_path))
      else:
        self.show_error_message(
            "Fichier introuvable",
            "Le fichier physique est introuvable ou a été déplacé.",
        )
    except Exception as e:
      self.show_error_message(
          "Erreur d'ouverture", f"Impossible d'ouvrir le document :\n{e}"
      )

  def _voir_fiche_interne(self, f):
    donnees_fiche = {
        "type_doc_interne": "fiche_fournisseur",
        "type_contact": "fournisseur",
        "numero": (
            "FICHE-FOUR-"
            f"{str(f.get('nom', 'INCONNU')).upper().replace(' ', '_')[:12]}"
        ),
        "date_creation": "-",
        "nom": f.get("nom", ""),
        "contact_nom": f.get("contact_nom", ""),
        "email": f.get("email", ""),
        "telephone": f.get("telephone", ""),
        "adresse": f.get("adresse", ""),
        "code_postal": f.get("code_postal", ""),
        "ville": f.get("ville", ""),
        "siret": f.get("siret", ""),
        "iban": f.get("iban", ""),
        "delai_paiement": f.get("delai_paiement", ""),
    }
    self.app.navigate_to(
        "PDFViewer", doc_type="fiche_fournisseur", doc_to_edit=donnees_fiche
    )

  # ─────────────────────────────────────────────────────────────────────────
  # LOGIQUE FORMULAIRE ET SYNCHRONISATION
  # ─────────────────────────────────────────────────────────────────────────
  def charger_fournisseur(self, idx, item):
    self.editing_idx = idx
    self.lbl_form_title.value = "✏️ Modifier la fiche fournisseur"
    self.lbl_form_title.color = "#D97706"
    self.btn_save.text = "💾 Appliquer les modifications"
    self.btn_save.bgcolor = "#D97706"
    self.lbl_status.value = "Mode modification actif"
    self.lbl_status.color = "#38BDF8"

    for key in self.entries:
      self.entries[key].value = item.get(key, "")
    if self.page:
      self.page.update()

  def vider_champs(self, e=None):
    self.editing_idx = None
    self.lbl_form_title.value = "📝 Ajouter un nouveau partenaire"
    self.lbl_form_title.color = self.accent_color
    self.btn_save.text = "💾 Enregistrer le Fournisseur"
    self.btn_save.bgcolor = "#15803D"
    self.lbl_status.value = ""
    for key in self.entries:
      self.entries[key].value = ""
    if self.page:
      self.page.update()

  def _valider_fournisseur(self, e):
    nom = self.entries["nom"].value.strip() if self.entries["nom"].value else ""
    if not nom:
      self.lbl_status.value = "Le Nom de la société est requis."
      self.lbl_status.color = "red400"
      if self.page:
        self.page.update()
      return

    fournisseurs = getattr(self.app, "fournisseurs", [])

    if self.editing_idx is not None:
      for key in self.entries:
        fournisseurs[self.editing_idx][key] = (
            self.entries[key].value.strip() if self.entries[key].value else ""
        )
    else:
      fourn_data = {
          key: (
              self.entries[key].value.strip() if self.entries[key].value else ""
          )
          for key in self.entries
      }
      fourn_data["documents_externes"] = []
      fournisseurs.append(fourn_data)

    if hasattr(self.app, "save_data"):
      self.app.save_data()
    self.refresh_fournisseur_list(None)
    self.vider_champs()

  def _supprimer_fournisseur(self, f):
    def confirm():
      fournisseurs = getattr(self.app, "fournisseurs", [])
      if "documents_externes" in f:
        for doc in f["documents_externes"]:
          try:
            file_path = Path(getattr(self.app, "data_dir", ".")) / doc["chemin"]
            if file_path.exists():
              os.remove(file_path)
          except Exception:
            pass
      if f in fournisseurs:
        fournisseurs.remove(f)
      if hasattr(self.app, "save_data"):
        self.app.save_data()
      self.opened_docs_idx = None
      self.refresh_fournisseur_list(None)
      self.vider_champs()

    self.show_confirm_dialog(
        "Confirmation",
        (
            f"Supprimer définitivement le partenaire '{f['nom']}' et TOUTES ses"
            " pièces jointes ?"
        ),
        confirm,
    )

  # ─────────────────────────────────────────────────────────────────────────
  # 📄 COMPOSANT 2 : TABLEAU DE SUIVI DES PIÈCES D'ACHATS (DataTable)
  # ─────────────────────────────────────────────────────────────────────────
  def _afficher_documents_achat(self):
    toolbar = ft.Row(
        controls=[
            ft.ElevatedButton(
                "➕ Nouveau Bon de Commande (BC)",
                bgcolor=self.accent_color,
                color="white",
                on_click=lambda e: self.app.navigate_to(
                    "CreateDocument", doc_type="bon_commande"
                ),
            ),
            ft.ElevatedButton(
                "➕ Nouveau Bon de Livraison (BL)",
                bgcolor=self.accent_color,
                color="white",
                on_click=lambda e: self.app.navigate_to(
                    "CreateDocument", doc_type="bon_livraison"
                ),
            ),
        ],
        spacing=10,
    )

    self.tree_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Type de Pièce")),
            ft.DataColumn(ft.Text("N° Document")),
            ft.DataColumn(ft.Text("Fournisseur")),
            ft.DataColumn(ft.Text("Date d'Émission")),
            ft.DataColumn(ft.Text("Montant Total (TTC)")),
            ft.DataColumn(ft.Text("Statut")),
        ],
        rows=[],
        expand=True,
    )

    table_container = ft.Container(
        content=ft.Column(
            controls=[self.tree_table], scroll=ft.ScrollMode.AUTO
        ),
        bgcolor="#141416",
        border_radius=12,
        border=ft.border.all(1, "#2A2A2E"),
        padding=10,
        expand=True,
    )

    actions_bar = ft.Row(
        controls=[
            ft.ElevatedButton(
                "👁️ Voir le PDF",
                bgcolor=self.accent_color,
                color="white",
                on_click=self._voir_pdf_selectionne,
            ),
            ft.OutlinedButton(
                "✏️ Modifier la pièce",
                on_click=self._modifier_document_selectionne,
            ),
            ft.ElevatedButton(
                "🗑️ Supprimer",
                bgcolor="#991B1B",
                color="white",
                on_click=self._supprimer_document_selectionne,
            ),
        ],
        spacing=10,
    )

    self.main_container.content = ft.Column(
        controls=[toolbar, table_container, actions_bar], expand=True
    )

    self._charger_pieces_achat()

  def _safe_float(self, val):
    if val is None:
      return 0.0
    if isinstance(val, (int, float)):
      return float(val)
    try:
      return float(str(val).replace("€", "").replace(" ", "").strip())
    except ValueError:
      return 0.0

  def _select_row(self, e, doc_type, doc_data):
    """Gère la surbrillation de ligne active au clic avec conversion explicite du booléen."""
    is_selected = str(e.data).lower() == "true"

    for r in self.tree_table.rows:
      r.selected = False

    if is_selected:
      e.control.selected = True
      self.selected_row_data = (doc_type, doc_data)
    else:
      self.selected_row_data = None

    if self.page:
      self.page.update()

  def _charger_pieces_achat(self):
    self.tree_table.rows.clear()
    self.selected_row_data = None

    def make_on_select(dtype, ddata):
      return lambda e: self._select_row(e, dtype, ddata)

    # Bons de commande
    for bc in getattr(self.app, "bons_commande", []):
      num = bc.get("numero", "Inconnu")
      f_info = bc.get("client", bc.get("fournisseur", {}))
      f_nom = (
          f_info.get("nom", "Inconnu")
          if isinstance(f_info, dict)
          else str(f_info)
      )
      total = f"{self._safe_float(bc.get('total_ttc', bc.get('montant_ttc', 0))):.2f} €"

      self.tree_table.rows.append(
          ft.DataRow(
              cells=[
                  ft.DataCell(ft.Text("🛒 Bon de Commande")),
                  ft.DataCell(ft.Text(num)),
                  ft.DataCell(ft.Text(f_nom)),
                  ft.DataCell(ft.Text(bc.get("date_creation", "-"))),
                  ft.DataCell(ft.Text(total)),
                  ft.DataCell(ft.Text(bc.get("statut", "Validé"))),
              ],
              on_select_changed=make_on_select("bon_commande", bc),
          )
      )

    # Bons de livraison
    for bl in getattr(self.app, "bons_livraison", []):
      num = bl.get("numero", "Inconnu")
      f_info = bl.get("client", bl.get("fournisseur", {}))
      f_nom = (
          f_info.get("nom", "Inconnu")
          if isinstance(f_info, dict)
          else str(f_info)
      )
      total = f"{self._safe_float(bl.get('total_ttc', bl.get('montant_ttc', 0))):.2f} €"

      self.tree_table.rows.append(
          ft.DataRow(
              cells=[
                  ft.DataCell(ft.Text("📦 Bon de Livraison")),
                  ft.DataCell(ft.Text(num)),
                  ft.DataCell(ft.Text(f_nom)),
                  ft.DataCell(ft.Text(bl.get("date_creation", "-"))),
                  ft.DataCell(ft.Text(total)),
                  ft.DataCell(ft.Text(bl.get("statut", "Reçu"))),
              ],
              on_select_changed=make_on_select("bon_livraison", bl),
          )
      )
    if self.page:
      self.page.update()

  def _voir_pdf_selectionne(self, e):
    if not self.selected_row_data:
      self.show_error_message(
          "Sélection requise",
          "Veuillez sélectionner un document d'achat à visualiser.",
      )
      return
    doc_type, doc_data = self.selected_row_data
    doc_data["type_doc_interne"] = doc_type
    self.app.navigate_to("PDFViewer", doc_type=doc_type, doc_to_edit=doc_data)

  def _modifier_document_selectionne(self, e):
    if not self.selected_row_data:
      self.show_error_message(
          "Sélection requise",
          "Veuillez sélectionner un document d'achat à modifier.",
      )
      return
    doc_type, doc_data = self.selected_row_data
    self.app.navigate_to(
        "CreateDocument", doc_type=doc_type, doc_to_edit=doc_data
    )

  def _supprimer_document_selectionne(self, e):
    if not self.selected_row_data:
      self.show_error_message(
          "Sélection requise", "Veuillez sélectionner une pièce à supprimer."
      )
      return
    doc_type, doc_data = self.selected_row_data

    def confirm():
      if doc_type == "bon_commande":
        getattr(self.app, "bons_commande", []).remove(doc_data)
      else:
        getattr(self.app, "bons_livraison", []).remove(doc_data)
      if hasattr(self.app, "save_data"):
        self.app.save_data()
      self._afficher_documents_achat()

    self.show_confirm_dialog(
        "Confirmation",
        f"Supprimer définitivement la pièce N° {doc_data.get('numero')} ?",
        confirm,
    )

  # ─────────────────────────────────────────────────────────────────────────
  # MODALS ET DIALOGUES NATIFS (overlay modernes)
  # ─────────────────────────────────────────────────────────────────────────
  def show_confirm_dialog(self, title, text, on_confirm):
    def close_dlg(e):
      dlg.open = False
      if self.page:
        self.page.update()

    def confirm_action(e):
      dlg.open = False
      if self.page:
        self.page.update()
      on_confirm()

    dlg = ft.AlertDialog(
        title=ft.Text(title),
        content=ft.Text(text),
        actions=[
            ft.TextButton("Oui", on_click=confirm_action),
            ft.TextButton("Non", on_click=close_dlg),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    if self.page:
      self.page.overlay.append(dlg)
      dlg.open = True
      self.page.update()

  def show_error_message(self, title, text):
    def close_dlg(e):
      dlg.open = False
      if self.page:
        self.page.update()

    dlg = ft.AlertDialog(
        title=ft.Text(title, color="red400"),
        content=ft.Text(text),
        actions=[
            ft.TextButton("OK", on_click=close_dlg),
        ],
    )
    if self.page:
      self.page.overlay.append(dlg)
      dlg.open = True
      self.page.update()
