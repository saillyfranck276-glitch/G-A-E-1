import csv
from datetime import datetime
import os
from pathlib import Path
import re
import flet as ft

# --- IMPORTS OPTIONNELS REPORTLAB & PYHANKO ---
REPORTLAB_AVAILABLE = False
try:
  from reportlab.lib import colors
  from reportlab.lib.pagesizes import A4
  from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
  from reportlab.pdfgen import canvas
  from reportlab.platypus import (
      Image,
      Paragraph,
      SimpleDocTemplate,
      Spacer,
      Table,
      TableStyle,
  )

  REPORTLAB_AVAILABLE = True
except ImportError:
  pass


def safe_border(width=1, color="#2A2A32"):
  """Bordure universelle sécurisée pour Serious Python / APK Android."""
  side = ft.BorderSide(width, color)
  return ft.Border(top=side, right=side, bottom=side, left=side)


class NumberedCanvas(canvas.Canvas if REPORTLAB_AVAILABLE else object):
  """Canvas personnalisé pour calculer le nombre total de pages et ajouter un pied de page propre."""

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self._saved_page_states = []

  def showPage(self):
    self._saved_page_states.append(dict(self.__dict__))
    self._startPage()

  def save(self):
    num_pages = len(self._saved_page_states)
    for state in self._saved_page_states:
      self.__dict__.update(state)
      self.draw_page_decorations(num_pages)
      super().showPage()
    super().save()

  def draw_page_decorations(self, page_count):
    self.saveState()
    self.setFont("Helvetica", 8)
    self.setFillColor(colors.HexColor("#6B7280"))

    self.setStrokeColor(colors.HexColor("#E5E7EB"))
    self.setLineWidth(0.5)
    self.line(35, 45, A4[0] - 35, 45)

    entreprise_nom = getattr(self, "_entreprise_nom", "Votre Entreprise")
    siret = getattr(self, "_entreprise_siret", "")
    mentions_custom = getattr(self, "_entreprise_mentions", "")

    if mentions_custom:
      mentions = (
          f"{entreprise_nom} — {mentions_custom[:100]}..."
          if len(mentions_custom) > 100
          else f"{entreprise_nom} — {mentions_custom}"
      )
    else:
      mentions = (
          f"{entreprise_nom} {f'- SIRET : {siret}' if siret else ''} — Document"
          " généré automatiquement."
      )

    self.drawString(35, 30, mentions)

    page_text = f"Page {self._pageNumber} sur {page_count}"
    self.drawRightString(A4[0] - 35, 30, page_text)
    self.restoreState()


class FacturationView(ft.Container):
  """Vue Flet pour la gestion des devis et factures (100 % Mobile & Desktop)."""

  def __init__(self, app):
    super().__init__()

    self.app = app
    self.expand = True
    self.padding = 10
    self.accent_color = "#2B719E"

    self.csv_picker = ft.FilePicker(on_result=self._on_csv_export_result)
    self.documents = {}
    self.selected_doc_key = None
    self.display_container = ft.Container(expand=True)

    try:
      if hasattr(self.app, "entreprise") and isinstance(
          self.app.entreprise, dict
      ):
        self.accent_color = self.app.entreprise.get("accent_color", "#2B719E")

      self._build_interface()
    except Exception as ex:
      self._render_error_ui(f"Erreur d'initialisation : {ex}")

  def did_mount(self):
    try:
      if self.page:
        if self.csv_picker not in self.page.overlay:
          self.page.overlay.append(self.csv_picker)

        self.page.on_resized = self._on_screen_resize
        self._refresh_table()
    except Exception as ex:
      self._render_error_ui(str(ex))

  def safe_update(self):
    try:
      if self.page:
        self.update()
    except Exception:
      pass

  def _render_error_ui(self, error_msg):
    self.content = ft.Container(
        padding=15,
        bgcolor="#3f1212",
        border_radius=10,
        border=safe_border(1, ft.colors.RED_700),
        content=ft.Column(
            [
                ft.Text(
                    "⚠️ Erreur dans la Facturation",
                    color=ft.colors.RED_300,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Text(error_msg, color="white", size=11, selectable=True),
            ],
            spacing=5,
        ),
    )
    self.safe_update()

  def _on_screen_resize(self, e):
    self._refresh_table()

  def _is_mobile(self):
    return self.page.width < 768 if self.page else False

  def _build_interface(self):
    header = ft.Row(
        controls=[
            ft.IconButton(
                icon=ft.icons.ARROW_BACK_ROUNDED,
                on_click=lambda e: self.app.navigate_to("Dashboard"),
            ),
            ft.Text("📂 Factures & Devis", size=20, weight=ft.FontWeight.BOLD),
        ],
        alignment=ft.MainAxisAlignment.START,
    )

    toolbar = ft.ResponsiveRow(
        controls=[
            ft.Column(
                [
                    ft.ElevatedButton(
                        "➕ Nouveau Devis",
                        bgcolor=self.accent_color,
                        color="white",
                        on_click=lambda e: self.app.navigate_to("NouveauDevis"),
                    )
                ],
                col={"sm": 6, "md": 3},
            ),
            ft.Column(
                [
                    ft.ElevatedButton(
                        "➕ Nouvelle Facture",
                        bgcolor=self.accent_color,
                        color="white",
                        on_click=lambda e: self.app.navigate_to(
                            "NouvelleFacture"
                        ),
                    )
                ],
                col={"sm": 6, "md": 3},
            ),
        ],
        spacing=10,
    )

    self.search_entry = ft.TextField(
        label="🔍 Rechercher (Numéro, client, statut...)",
        bgcolor="#1A1A1C",
        height=45,
        text_size=13,
        on_change=self._refresh_table,
        expand=True,
    )

    self.table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Type", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Numéro", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Client", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Total TTC", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("Statut", weight=ft.FontWeight.BOLD)),
            ft.DataColumn(ft.Text("URSSAF", weight=ft.FontWeight.BOLD)),
        ],
        rows=[],
        heading_row_color="#242426",
        show_checkbox_column=False,
    )

    def btn_grid(text, icon_name, color, action):
      return ft.Column(
          [
              ft.ElevatedButton(
                  content=ft.Row(
                      [ft.Icon(icon_name, size=16), ft.Text(text, size=12)],
                      spacing=6,
                      alignment=ft.MainAxisAlignment.CENTER,
                  ),
                  bgcolor=color,
                  color="white",
                  on_click=action,
                  style=ft.ButtonStyle(padding=10),
              )
          ],
          col={"sm": 6, "md": 3, "lg": 3},
      )

    actions_grid = ft.ResponsiveRow(
        controls=[
            btn_grid(
                "Voir PDF",
                ft.icons.PICTURE_AS_PDF,
                "#2B719E",
                self.ouvrir_pdf_selectionne,
            ),
            btn_grid(
                "Générer PDF",
                ft.icons.SAVE_ALT,
                "#8B5CF6",
                self.exporter_pdf_organise,
            ),
            btn_grid(
                "Modifier", ft.icons.EDIT, "#F59E0B", self.modifier_selectionne
            ),
            btn_grid(
                "Marquer Payée", ft.icons.EURO, "#10B981", self.marquer_payee
            ),
            btn_grid(
                "URSSAF", ft.icons.CHECK_CIRCLE, "#16A34A", self.declarer_urssaf
            ),
            btn_grid(
                "Convertir Devis",
                ft.icons.TRANSFORM,
                "#0EA5E9",
                self.convertir_devis_en_facture,
            ),
            btn_grid(
                "Export CSV", ft.icons.TABLE_CHART, "#4F46E5", self.exporter_csv
            ),
            btn_grid(
                "Supprimer",
                ft.icons.DELETE,
                "#DC2626",
                self.supprimer_selectionne,
            ),
        ],
        spacing=8,
    )

    self.content = ft.Column(
        controls=[
            header,
            toolbar,
            ft.Row([self.search_entry]),
            self.display_container,
            actions_grid,
        ],
        spacing=12,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

  def _refresh_table(self, e=None):
    try:
      self.documents.clear()
      self.table.rows.clear()
      query = (
          self.search_entry.value.strip().lower()
          if self.search_entry and self.search_entry.value
          else ""
      )

      filtered_docs = []

      devis_raw = getattr(self.app, "devis", [])
      devis_list = devis_raw if isinstance(devis_raw, list) else []
      for devis in devis_list:
        if self._match_query(devis, "devis", query):
          filtered_docs.append((devis, "devis"))

      factures_raw = getattr(self.app, "factures", [])
      factures_list = factures_raw if isinstance(factures_raw, list) else []
      for facture in factures_list:
        if self._match_query(facture, "facture", query):
          filtered_docs.append((facture, "facture"))

      if self._is_mobile():
        self._render_mobile_cards(filtered_docs)
      else:
        self._render_desktop_table(filtered_docs)

      self.safe_update()
    except Exception as ex:
      print(f"Erreur _refresh_table : {ex}")

  def _render_desktop_table(self, docs):
    for doc, type_doc in docs:
      self._insert_document_row(doc, type_doc)

    self.display_container.content = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(controls=[self.table], scroll=ft.ScrollMode.AUTO)
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        ),
        bgcolor="#141416",
        border_radius=12,
        border=safe_border(1, "#2A2A2E"),
        padding=10,
        height=300,
    )

  def _render_mobile_cards(self, docs):
    cards_list = []

    for doc, type_doc in docs:
      num = str(doc.get("numero", ""))
      key = (type_doc, num)
      self.documents[key] = doc

      client = doc.get("client", {})
      nom = (
          client.get("nom", "Inconnu")
          if isinstance(client, dict)
          else str(client)
      )
      statut = doc.get("statut", "-")
      total_ttc = f"{float(doc.get('total_ttc', 0)):.2f} €"
      is_selected = self.selected_doc_key == key

      def make_select_handler(k):
        return lambda e: self._select_card(k)

      card_content = ft.Container(
          bgcolor="#1E1E22" if not is_selected else "#2A3A4E",
          border=safe_border(
              1.5 if is_selected else 1,
              self.accent_color if is_selected else "#2A2A32",
          ),
          border_radius=10,
          padding=12,
          on_click=make_select_handler(key),
          content=ft.Column(
              [
                  ft.Row(
                      [
                          ft.Container(
                              content=ft.Text(
                                  type_doc.upper(),
                                  size=10,
                                  weight=ft.FontWeight.BOLD,
                                  color="white",
                              ),
                              bgcolor=(
                                  self.accent_color
                                  if type_doc == "facture"
                                  else "#8B5CF6"
                              ),
                              padding=ft.padding.horizontal(8),
                              border_radius=4,
                          ),
                          ft.Text(
                              num,
                              weight=ft.FontWeight.BOLD,
                              color="white",
                              size=14,
                          ),
                          ft.Text(
                              total_ttc,
                              weight=ft.FontWeight.BOLD,
                              color=(
                                  "#10B981"
                                  if type_doc == "facture"
                                  else "#2B719E"
                              ),
                              size=14,
                          ),
                      ],
                      alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                  ),
                  ft.Text(f"Client : {nom}", size=12, color="#AEAEB2"),
                  ft.Row(
                      [
                          ft.Text(
                              f"Statut : {statut}",
                              size=11,
                              color=(
                                  "#34D399"
                                  if "Payée" in statut
                                  else "#F59E0B"
                              ),
                          ),
                          ft.Text(
                              f"URSSAF : {'Oui' if doc.get('urssaf_declare') else 'Non'}",
                              size=11,
                              color="#AEAEB2",
                          ),
                      ],
                      alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                  ),
              ],
              spacing=6,
          ),
      )
      cards_list.append(card_content)

    if not cards_list:
      cards_list.append(
          ft.Text("Aucun document trouvé.", color="#AEAEB2", size=13)
      )

    self.display_container.content = ft.Column(
        controls=cards_list, spacing=10, expand=True
    )

  def _select_card(self, key):
    self.selected_doc_key = key
    self._refresh_table()

  def _match_query(self, doc, type_doc, query):
    if not query:
      return True
    num = str(doc.get("numero", "")).lower()
    client = doc.get("client", {})
    nom = (
        client.get("nom", "").lower()
        if isinstance(client, dict)
        else str(client).lower()
    )
    statut = str(doc.get("statut", "")).lower()
    return (
        query in num or query in nom or query in statut or query in type_doc
    )

  def _insert_document_row(self, doc, type_doc):
    num = str(doc.get("numero", ""))
    key = (type_doc, num)
    self.documents[key] = doc

    client = doc.get("client", {})
    nom = (
        client.get("nom", "Inconnu")
        if isinstance(client, dict)
        else str(client)
    )
    statut = doc.get("statut", "-")
    if statut == "Payée" and doc.get("date_paiement"):
      statut = f"Payée ({doc.get('date_paiement')})"

    total_ttc = f"{float(doc.get('total_ttc', 0)):.2f} €"
    urssaf = "Oui" if doc.get("urssaf_declare") else "Non"
    row = ft.DataRow(cells=[])

    def handle_single_tap(e):
      for r in self.table.rows:
        r.selected = False
      row.selected = True
      self.selected_doc_key = key
      self.safe_update()

    def handle_double_tap(e):
      handle_single_tap(e)
      self.exporter_pdf_direct(type_doc, doc, ouvrir_apres=True)

    def create_clickable_cell(text, color=None, weight=None):
      return ft.DataCell(
          ft.GestureDetector(
              content=ft.Container(
                  content=ft.Text(text, color=color, weight=weight),
                  alignment=ft.Alignment(-1, 0),
                  bgcolor="transparent",
                  expand=True,
              ),
              on_tap=handle_single_tap,
              on_double_tap=handle_double_tap,
          )
      )

    row.cells = [
        create_clickable_cell(
            type_doc.capitalize(), weight=ft.FontWeight.W_500
        ),
        create_clickable_cell(num),
        create_clickable_cell(nom),
        create_clickable_cell(
            total_ttc, color="#10B981" if type_doc == "facture" else "#2B719E"
        ),
        create_clickable_cell(statut),
        create_clickable_cell(
            urssaf, color="#10B981" if urssaf == "Oui" else "#636366"
        ),
    ]
    self.table.rows.append(row)

  def _selected_document(self):
    if not self.selected_doc_key:
      self.show_snack(
          "Veuillez d'abord sélectionner un document.", is_error=True
      )
      return None, None
    type_doc, num_doc = self.selected_doc_key
    return type_doc, self.documents.get((type_doc, num_doc))

  def ouvrir_pdf_selectionne(self, e=None):
    type_doc, doc = self._selected_document()
    if doc:
      self.exporter_pdf_direct(type_doc, doc, ouvrir_apres=True)

  def exporter_pdf_organise(self, e=None):
    type_doc, doc = self._selected_document()
    if doc:
      self.exporter_pdf_direct(type_doc, doc, ouvrir_apres=False)

  def _trouver_chemin_valide(self, chemin_initial):
    if not chemin_initial:
      return ""

    p_init = Path(chemin_initial)
    if p_init.exists():
      return str(p_init.resolve())

    base_dirs = []
    if hasattr(self.app, "data_dir") and self.app.data_dir:
      base_dirs.append(Path(self.app.data_dir))

    base_dirs.extend(
        [Path.cwd(), Path(__file__).parent, Path(__file__).parent / "assets"]
    )

    for d in base_dirs:
      t1 = d / p_init.name
      if t1.exists():
        return str(t1.resolve())
      t2 = d / chemin_initial
      if t2.exists():
        return str(t2.resolve())
    return ""

  def exporter_pdf_direct(self, type_doc, doc, ouvrir_apres=False):
    if not REPORTLAB_AVAILABLE:
      return self.show_snack(
          "ReportLab n'est pas disponible pour générer des PDF.", is_error=True
      )

    date_str = doc.get("date_creation", datetime.now().strftime("%d/%m/%Y"))
    try:
      parts = date_str.split("/")
      j, m, a = parts[0], parts[1], parts[2]
    except Exception:
      now = datetime.now()
      j, m, a = f"{now.day:02d}", f"{now.month:02d}", f"{now.year}"

    # Répertoire sécurisé Android / Desktop
    if hasattr(self.app, "data_dir") and self.app.data_dir:
      base_dir = Path(self.app.data_dir) / "Documents_PDF"
    else:
      base_dir = Path(__file__).parent / "data" / "Documents_PDF"

    folder_path = base_dir / type_doc.capitalize() / a / m

    try:
      folder_path.mkdir(parents=True, exist_ok=True)
      file_name = f"{doc.get('numero', 'SANS_NUMERO')}.pdf"
      full_path = folder_path / file_name

      self._generate_pdf_file(type_doc, doc, str(full_path))

      doc["pdf_path"] = str(full_path)
      doc["pdf_to_load"] = str(full_path)
      doc["type_doc_interne"] = type_doc

      if ouvrir_apres:
        if hasattr(self.app, "navigate_to"):
          self.app.current_doc = doc
          self.app.navigate_to("PDFViewer")
        else:
          self.show_snack(f"PDF généré : {file_name}")
      else:
        self.show_snack(f"⚡ PDF enregistré dans le dossier de l'app")
    except Exception as ex:
      self.show_snack(f"Erreur création PDF : {ex}", is_error=True)

  def _generate_pdf_file(self, type_doc, doc, file_path):
    doc_pdf = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=35,
        leftMargin=35,
        topMargin=35,
        bottomMargin=45,
    )
    story = []
    styles = getSampleStyleSheet()

    ent = getattr(self.app, "entreprise", {})
    ent_nom = ent.get("nom", "MA SOCIÉTÉ").upper()
    ent_siret = ent.get("siret", "")
    ent_adresse = ent.get("adresse", "Adresse non renseignée")
    ent_cp = ent.get("code_postal", ent.get("cp", ""))
    ent_ville = ent.get("ville", "")
    ent_email = ent.get("email", "")
    ent_tel = ent.get("telephone", "")

    ent_bloc_adresse = f"{ent_adresse}"
    if ent_cp or ent_ville:
      ent_bloc_adresse += f"<br/>{ent_cp} {ent_ville}".strip()

    type_labels = {
        "devis": "DEVIS",
        "facture": "FACTURE",
        "bl": "BON DE LIVRAISON",
        "bc": "BON DE COMMANDE",
    }
    label_doc = type_labels.get(type_doc.lower(), type_doc.upper())

    style_ent_body = ParagraphStyle(
        "EntBody",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#4B5563"),
    )
    style_doc_meta = ParagraphStyle(
        "DocMeta",
        fontName="Helvetica",
        fontSize=9,
        leading=14,
        textColor=colors.HexColor("#111827"),
        alignment=2,
    )
    style_client_body = ParagraphStyle(
        "CliBody",
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#111827"),
    )

    cell_text = ParagraphStyle(
        "CellText",
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#111827"),
    )
    cell_right = ParagraphStyle(
        "CellRight",
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#111827"),
        alignment=2,
    )
    cell_right_bold = ParagraphStyle(
        "CellRightBold",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#111827"),
        alignment=2,
    )

    mentions_text = ent.get(
        "mentions_legales",
        f"SIRET : {ent_siret} - Enregistré conformément à la loi.",
    )

    txt_entreprise = f"<b>{ent_nom}</b><br/>{ent_bloc_adresse}<br/>"
    if ent_tel:
      txt_entreprise += f"Tel : {ent_tel}<br/>"
    if ent_email:
      txt_entreprise += f"Email : {ent_email}<br/>"
    if ent_siret:
      txt_entreprise += f"SIRET : {ent_siret}"

    entreprise_elements = []
    logo_path = self._trouver_chemin_valide(
        ent.get("logo_path", ent.get("logo", ""))
    )
    if logo_path:
      try:
        entreprise_elements.append(Image(logo_path, width=110, height=45))
        entreprise_elements.append(Spacer(1, 8))
      except Exception:
        pass
    entreprise_elements.append(Paragraph(txt_entreprise, style_ent_body))

    num = doc.get("numero", "INCONNU")
    date_crea = doc.get("date_creation", "-")
    txt_metadonnees = (
        f"<font size=20 color='{self.accent_color}'><b>{label_doc}</b></font><br/><br/>"
    )
    txt_metadonnees += f"<b>N° :</b> {num}<br/>"
    txt_metadonnees += f"<b>Date :</b> {date_crea}<br/>"

    header_table = Table(
        [[entreprise_elements, Paragraph(txt_metadonnees, style_doc_meta)]],
        colWidths=[260, 265],
    )
    header_table.setStyle(
        TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")])
    )
    story.append(header_table)
    story.append(Spacer(1, 25))

    c_info = doc.get("client", {})
    nom_c = (
        c_info.get("nom", "Inconnu") if isinstance(c_info, dict) else str(c_info)
    )
    prenom_c = (
        c_info.get("prenom", c_info.get("prénom", ""))
        if isinstance(c_info, dict)
        else ""
    )
    adr_c = (
        c_info.get("adresse", "Adresse non renseignée")
        if isinstance(c_info, dict)
        else ""
    )
    cp_c = (
        c_info.get("code_postal", c_info.get("cp", ""))
        if isinstance(c_info, dict)
        else ""
    )
    ville_c = c_info.get("ville", "") if isinstance(c_info, dict) else ""
    tel_c = c_info.get("telephone", "") if isinstance(c_info, dict) else ""

    cli_bloc_adresse = f"{adr_c}"
    if cp_c or ville_c:
      cli_bloc_adresse += f"<br/>{cp_c} {ville_c}".strip()

    identite_client = f"{prenom_c} {nom_c}".strip() if prenom_c else nom_c
    txt_client = f"<b>DESTINATAIRE</b><br/><b>{identite_client}</b><br/>{cli_bloc_adresse}"
    if tel_c:
      txt_client += f"<br/>Tel : {tel_c}"

    client_table = Table(
        [["", Paragraph(txt_client, style_client_body)]], colWidths=[260, 265]
    )
    client_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#F9FAFB")),
            ("PADDING", (1, 0), (1, 0), 12),
            ("BOX", (1, 0), (1, 0), 0.5, colors.HexColor("#E5E7EB")),
        ])
    )
    story.append(client_table)
    story.append(Spacer(1, 30))

    headers = [
        Paragraph(
            "<b>Désignation</b>",
            ParagraphStyle(
                "H1",
                fontName="Helvetica-Bold",
                fontSize=9,
                textColor=colors.white,
            ),
        ),
        Paragraph(
            "<b>Qté</b>",
            ParagraphStyle(
                "H2",
                fontName="Helvetica-Bold",
                fontSize=9,
                textColor=colors.white,
                alignment=2,
            ),
        ),
        Paragraph(
            "<b>Prix U. HT</b>",
            ParagraphStyle(
                "H3",
                fontName="Helvetica-Bold",
                fontSize=9,
                textColor=colors.white,
                alignment=2,
            ),
        ),
        Paragraph(
            "<b>Total HT</b>",
            ParagraphStyle(
                "H4",
                fontName="Helvetica-Bold",
                fontSize=9,
                textColor=colors.white,
                alignment=2,
            ),
        ),
    ]
    table_data = [headers]

    lines = doc.get("lignes", doc.get("articles", []))
    for item in lines:
      des = item.get("designation", item.get("nom", "Prestation"))
      qte = str(item.get("quantite", item.get("qte", 1)))
      pu = f"{float(item.get('prix_unitaire', item.get('prix', 0))):.2f} €"
      tot = f"{float(item.get('total_ht', item.get('montant', 0))):.2f} €"
      table_data.append([
          Paragraph(des, cell_text),
          Paragraph(qte, cell_right),
          Paragraph(pu, cell_right),
          Paragraph(tot, cell_right),
      ])

    tot_ht = f"{float(doc.get('total_ht', doc.get('montant_ht', 0))):.2f} €"
    tot_tva = f"{float(doc.get('tva', doc.get('montant_tva', 0))):.2f} €"
    tot_ttc = f"{float(doc.get('total_ttc', doc.get('montant_ttc', 0))):.2f} €"

    table_data.append([
        "",
        "",
        Paragraph("Total HT", cell_right_bold),
        Paragraph(tot_ht, cell_right),
    ])
    table_data.append([
        "",
        "",
        Paragraph("TVA", cell_right_bold),
        Paragraph(tot_tva, cell_right),
    ])
    table_data.append([
        "",
        "",
        Paragraph("Total TTC", cell_right_bold),
        Paragraph(tot_ttc, cell_right_bold),
    ])

    t_lines = Table(table_data, colWidths=[285, 40, 100, 100])
    ts = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(self.accent_color)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
    ])

    for i in range(1, len(lines) + 1):
      ts.add(
          "BACKGROUND",
          (0, i),
          (-1, i),
          (
              colors.HexColor("#FFFFFF")
              if i % 2 != 0
              else colors.HexColor("#F9FAFB")
          ),
      )
      ts.add("LINEBELOW", (0, i), (-1, i), 0.5, colors.HexColor("#F3F4F6"))

    ts.add("LINEABOVE", (2, -3), (3, -3), 1, colors.HexColor("#E5E7EB"))
    ts.add("BACKGROUND", (2, -1), (3, -1), colors.HexColor("#F3F4F6"))
    t_lines.setStyle(ts)
    story.append(t_lines)

    story.append(Spacer(1, 30))
    signature_elements = []

    if type_doc.lower() in ["devis", "bc"]:
      signature_elements.append(
          Paragraph(
              "<b>Bon pour accord</b><br/><font size=7 color='#6B7280'>Mention"
              " 'Lu et approuvé' obligatoire :</font>",
              cell_text,
          )
      )
    else:
      signature_elements.append(
          Paragraph("<b>Cachet &amp; Signature</b>", cell_text)
      )

    signature_elements.append(Spacer(1, 5))

    sig_raw_path = doc.get(
        "signature_path",
        doc.get("signature_img_path", ent.get("signature_pad", "")),
    )
    sig_img_path = self._trouver_chemin_valide(sig_raw_path)

    if sig_img_path:
      try:
        signature_elements.append(Image(sig_img_path, width=150, height=50))
      except Exception:
        signature_elements.append(Spacer(1, 50))
    else:
      signature_elements.append(Spacer(1, 50))

    moment_signature = datetime.now().strftime("%d/%m/%Y à %H:%M")
    signature_elements.append(Spacer(1, 4))
    signature_elements.append(
        Paragraph(
            f"<font size=7.5 color='#1F2937'><b>Signé électroniquement le"
            f" {moment_signature}</b></font>",
            ParagraphStyle("SigSub", fontName="Helvetica-Bold"),
        )
    )

    tab_signature = Table([["", signature_elements]], colWidths=[325, 200])
    tab_signature.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#F9FAFB")),
            ("PADDING", (1, 0), (1, 0), 12),
            ("BOX", (1, 0), (1, 0), 0.75, colors.HexColor("#D1D5DB")),
            ("LINEBELOW", (1, 0), (1, 0), 2, colors.HexColor(self.accent_color)),
        ])
    )
    story.append(tab_signature)

    story.append(Spacer(1, 20))
    story.append(
        Paragraph(
            f"<b>Mentions légales :</b> {mentions_text}",
            ParagraphStyle(
                "MentionsCorp",
                fontName="Helvetica-Oblique",
                fontSize=7.5,
                leading=11,
                textColor=colors.HexColor("#6B7280"),
            ),
        )
    )

    canvas_maker = NumberedCanvas
    canvas_maker._entreprise_nom = ent_nom
    canvas_maker._entreprise_siret = ent_siret
    canvas_maker._entreprise_mentions = mentions_text
    doc_pdf.build(story, canvasmaker=canvas_maker)

    pfx_path = ent.get("signature_pfx_path")
    pfx_password = ent.get("signature_pfx_password")
    if pfx_path and os.path.exists(pfx_path):
      self._apply_invisible_signature(file_path, pfx_path, pfx_password)

  def _apply_invisible_signature(self, file_path, pfx_path, pfx_password):
    try:
      from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
      from pyhanko.sign import fields, sign_pdf
      from pyhanko.sign.signer import SimpleSigner

      password_bytes = pfx_password.encode("utf-8") if pfx_password else None
      signer = SimpleSigner.load_pkcs12(pfx_path, passphrase=password_bytes)

      with open(file_path, "rb+") as f:
        w = IncrementalPdfFileWriter(f)
        fields.append_signature_field(
            w,
            sig_field_spec=fields.SigFieldSpec(
                sig_field_name="SignatureInvisible"
            ),
        )
        meta = sign_pdf.PdfSignatureMetadata(field_name="SignatureInvisible")
        sign_pdf.sign_pdf(w, meta, signer=signer, output=f)
    except Exception:
      pass

  def modifier_selectionne(self, e=None):
    type_doc, doc = self._selected_document()
    if not doc:
      return

    try:
      from views.create_document import CreateDocumentView

      if hasattr(self.app, "content_area"):
        self.app.content_area.content = CreateDocumentView(
            app=self.app, doc_type=type_doc, doc_to_edit=doc
        )
      self.safe_update()
    except Exception as ex:
      self.show_snack(
          f"Impossible de charger le formulaire d'édition : {ex}", is_error=True
      )

  def supprimer_selectionne(self, e=None):
    type_doc, doc = self._selected_document()
    if not doc:
      return

    def confirmation_action(confirme):
      dialog.open = False
      self.safe_update()
      if confirme:
        if type_doc == "devis":
          if hasattr(self.app, "devis") and doc in self.app.devis:
            self.app.devis.remove(doc)
        else:
          if hasattr(self.app, "factures") and doc in self.app.factures:
            self.app.factures.remove(doc)
        if hasattr(self.app, "save_data"):
          self.app.save_data()
        self.selected_doc_key = None
        self._refresh_table()
        self.show_snack("Le document a été supprimé.")

    dialog = ft.AlertDialog(
        title=ft.Text("🚨 Suppression"),
        content=ft.Text(f"Supprimer le {type_doc} n°{doc.get('numero', '')} ?"),
        actions=[
            ft.TextButton(
                "Annuler", on_click=lambda _: confirmation_action(False)
            ),
            ft.ElevatedButton(
                "Supprimer",
                bgcolor=ft.colors.RED_700,
                color="white",
                on_click=lambda _: confirmation_action(True),
            ),
        ],
    )
    if self.page:
      self.page.overlay.append(dialog)
      dialog.open = True
      self.safe_update()

  def marquer_payee(self, e=None):
    type_doc, doc = self._selected_document()
    if not doc:
      return
    if type_doc != "facture":
      return self.show_snack("Factures uniquement.", is_error=True)

    date_aujourdhui = datetime.now().strftime("%d/%m/%Y")
    doc["statut"] = "Payée"
    doc["date_paiement"] = date_aujourdhui
    if hasattr(self.app, "save_data"):
      self.app.save_data()
    self._refresh_table()
    self.show_snack("Facture payée ! 💶")

  def _next_invoice_number(self):
    factures_list = getattr(self.app, "factures", [])
    if not isinstance(factures_list, list):
      factures_list = []
    return f"FAC-{len(factures_list) + 1:03d}"

  def declarer_urssaf(self, e=None):
    type_doc, doc = self._selected_document()
    if not doc or type_doc != "facture":
      return
    doc["urssaf_declare"] = True
    doc["statut"] = "Déclarée"
    if hasattr(self.app, "save_data"):
      self.app.save_data()
    self._refresh_table()
    self.show_snack("Marquée URSSAF. ✅")

  def convertir_devis_en_facture(self, e=None):
    type_doc, doc = self._selected_document()
    if not doc or type_doc != "devis":
      return

    nouvelle_facture = {
        "numero": self._next_invoice_number(),
        "client": doc.get("client"),
        "lignes": list(doc.get("lignes", doc.get("articles", []))),
        "total_ht": doc.get("total_ht", 0),
        "tva": doc.get("tva", 0),
        "total_ttc": doc.get("total_ttc", 0),
        "date_creation": datetime.now().strftime("%d/%m/%Y"),
        "statut": "À payer",
        "urssaf_declare": False,
    }
    if hasattr(self.app, "factures"):
      if not isinstance(self.app.factures, list):
        self.app.factures = []
      self.app.factures.append(nouvelle_facture)
    doc["statut"] = "Converti"
    if hasattr(self.app, "save_data"):
      self.app.save_data()
    self._refresh_table()
    self.show_snack("Facture créée ! 🔄")

  def exporter_csv(self, e=None):
    try:
      self.csv_picker.save_file(
          file_name="historique_comptable.csv", allowed_extensions=["csv"]
      )
    except Exception as ex:
      self.show_snack(f"Erreur export CSV : {ex}", is_error=True)

  def _on_csv_export_result(self, e: ft.FilePickerResultEvent):
    if e.path:
      try:
        with open(e.path, mode="w", newline="", encoding="utf-8-sig") as f:
          writer = csv.writer(f, delimiter=";")
          writer.writerow(
              ["Type", "Numéro", "Client", "Total TTC", "Statut"]
          )
          factures_list = getattr(self.app, "factures", [])
          if isinstance(factures_list, list):
            for f_doc in factures_list:
              client_val = f_doc.get("client", {})
              nom_client = (
                  client_val.get("nom")
                  if isinstance(client_val, dict)
                  else str(client_val)
              )
              writer.writerow([
                  "Facture",
                  f_doc.get("numero"),
                  nom_client,
                  f_doc.get("total_ttc"),
                  f_doc.get("statut"),
              ])
        self.show_snack("Export CSV réussi ! ✔")
      except Exception as ex:
        self.show_snack(f"Erreur d'export CSV : {ex}", is_error=True)

  def show_snack(self, message, is_error=False):
    if self.page:
      self.page.snack_bar = ft.SnackBar(
          content=ft.Text(message),
          bgcolor=ft.colors.RED_700 if is_error else ft.colors.GREEN_700,
      )
      self.page.snack_bar.open = True
      self.safe_update()
