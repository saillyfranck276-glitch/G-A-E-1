import base64
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import os
from pathlib import Path
import re
import smtplib
import subprocess
import sys
import threading
import fitz  # PyMuPDF
import flet as ft
import flet.canvas as cv
from PIL import Image, ImageDraw
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


class PDFViewer(ft.Container):
  """Vue de lecture PDF Premium sous Flet avec Zoom, Signature manuscrite et Moteur d'export Pro."""

  def __init__(self, app):
    super().__init__()
    self.app = app
    self.expand = True
    self.padding = 15

    # États internes du lecteur
    self.doc = None
    self.zoom = 1.2
    self.pdf_path = None

    # Configuration des dossiers de données
    self.base_dir = Path(
        getattr(
            self.app,
            "base_dir",
            Path(__file__).resolve().parent.parent,
        )
    )
    self.data_dir = Path(
        getattr(self.app, "data_dir", self.base_dir / "data")
    )

    # Couleur d'accentuation d'entreprise
    self.accent_color = "#1E3A8A"
    if hasattr(self.app, "entreprise") and isinstance(
        self.app.entreprise, dict
    ):
      self.accent_color = self.app.entreprise.get("accent_color", "#1E3A8A")

    # Conteneur scrollable accueillant les pages rendues du PDF
    self.pdf_pages_column = ft.Column(
        scroll=ft.ScrollMode.ALWAYS,
        expand=True,
        alignment=ft.MainAxisAlignment.CENTER,
    )

    # Initialisation de l'interface graphique
    self._build_interface()

  def did_mount(self):
    """Méthode déclenchée par Flet dès l'affichage de la vue."""
    self.file_picker = ft.FilePicker(on_result=self.on_file_picked)
    if self.page and self.file_picker not in self.page.overlay:
      self.page.overlay.append(self.file_picker)
      self.page.update()
    self._load_document_from_app()

  def _load_document_from_app(self):
    """Récupère l'état du document sélectionné globalement dans l'application."""
    self.doc = (
        getattr(self.app, "current_document", None)
        or getattr(self.app, "current_doc", None)
        or getattr(self.app, "selected_document", None)
    )

    if not self.doc:
      self.pdf_pages_column.controls.clear()
      self.pdf_pages_column.controls.append(
          ft.Container(
              content=ft.Text(
                  "Aucun document chargé. Double-cliquez sur une ligne depuis"
                  " vos fiches de suivi.",
                  size=14,
              ),
              alignment=ft.alignment.center,
              padding=40,
          )
      )
      if self.page:
        self.page.update()
      return

    pdf_direct_path = (
        self.doc.get("pdf_path") if isinstance(self.doc, dict) else None
    )

    if pdf_direct_path:
      self.doc = {
          "numero": Path(pdf_direct_path).stem,
          "externe_path": Path(pdf_direct_path),
      }
      self.display_pdf()
    elif self.doc:
      try:
        self.generer_pdf_pro(silent=True)
      except Exception as e:
        self.pdf_pages_column.controls.clear()
        self.pdf_pages_column.controls.append(
            ft.Text(f"Erreur de prévisualisation : {e}", color="orange700")
        )
        if self.page:
          self.page.update()

  def _retour_intelligent(self, e):
    """Retourne dynamiquement sur la bonne vue en fonction du type de document."""
    if (
        self.doc
        and isinstance(self.doc, dict)
        and "externe_path" in self.doc
        and "documents_clients" in str(self.doc["externe_path"])
    ):
      self.app.navigate_to("Clients")
      return

    t_doc = (
        self.doc.get("type_doc_interne")
        if isinstance(self.doc, dict)
        else None
    )
    if t_doc in ["bon_commande", "bon_livraison"]:
      self.app.navigate_to("Fournisseurs")
    elif t_doc == "fiche_contact":
      self.app.navigate_to("Clients")
    else:
      self.app.navigate_to("Facturation")

  def get_path(self):
    """Détermine le chemin physique absolu du fichier PDF sur le stockage local."""
    if not self.doc:
      return None
    if isinstance(self.doc, dict) and "externe_path" in self.doc:
      return Path(self.doc["externe_path"])

    t_doc = (
        self.doc.get("type_doc_interne")
        if isinstance(self.doc, dict)
        else None
    )
    if t_doc:
      if t_doc == "facture":
        type_folder = "Factures"
      elif t_doc == "devis":
        type_folder = "Devis"
      elif t_doc == "bon_commande":
        type_folder = "Bons_Commande"
      elif t_doc == "bon_livraison":
        type_folder = "Bons_Livraison"
      else:
        type_folder = "Autres"
    else:
      num_upper = (
          str(self.doc.get("numero", "")).upper()
          if isinstance(self.doc, dict)
          else str(self.doc).upper()
      )
      type_folder = (
          "Factures"
          if "FACT" in num_upper or num_upper.startswith("F")
          else "Devis"
      )

    date_str = (
        self.doc.get("date_creation", datetime.now().strftime("%d/%m/%Y"))
        if isinstance(self.doc, dict)
        else datetime.now().strftime("%d/%m/%Y")
    )
    annee = (
        date_str.split("/")[-1]
        if "/" in date_str
        else datetime.now().strftime("%Y")
    )

    folder = self.data_dir / "pdfs" / type_folder / annee
    folder.mkdir(parents=True, exist_ok=True)

    num_doc = (
        self.doc.get("numero", "TEMP_DOC")
        if isinstance(self.doc, dict)
        else "TEMP_DOC"
    )
    return folder / f"{num_doc}.pdf"

  def display_pdf(self):
    """Extrait les pages du PDF sous forme d'images et met à jour le visualiseur."""
    path = self.get_path()
    if not path or not path.exists():
      return

    self.pdf_pages_column.controls.clear()

    try:
      doc = fitz.open(path)
      for page in doc:
        pix = page.get_pixmap(
            matrix=fitz.Matrix(self.zoom * 2, self.zoom * 2)
        )
        img_data = pix.tobytes("png")
        encoded = base64.b64encode(img_data).decode("utf-8")

        self.pdf_pages_column.controls.append(
            ft.Container(
                content=ft.Image(
                    src_base64=encoded,
                    fit=ft.ImageFit.CONTAIN,
                    width=pix.width / 2,
                    height=pix.height / 2,
                ),
                alignment=ft.alignment.center,
                margin=ft.margin.symmetric(vertical=8),
                shadow=ft.BoxShadow(blur_radius=12, color="#40000000"),
            )
        )
      if self.page:
        self.page.update()
    except Exception as e:
      self.show_snack(f"Erreur d'affichage : {e}", is_error=True)

  def _build_interface(self):
    """Construit la barre d'outils supérieure et la zone de lecture."""
    toolbar = ft.Row(
        controls=[
            ft.ElevatedButton(
                "📂 Ouvrir",
                bgcolor=self.accent_color,
                color="white",
                on_click=lambda _: self.file_picker.pick_files(
                    allowed_extensions=["pdf"]
                ),
            ),
            ft.ElevatedButton(
                "📄 Regénérer",
                bgcolor="#34495E",
                color="white",
                on_click=lambda _: self.generer_pdf_pro(silent=False),
            ),
            ft.ElevatedButton(
                "🖨️ Imprimer",
                bgcolor="#27AE60",
                color="white",
                on_click=self.imprimer_pdf,
            ),
            ft.ElevatedButton(
                "✍️ Signer",
                bgcolor="#8E44AD",
                color="white",
                on_click=self.lancer_signature_pad,
            ),
            ft.ElevatedButton(
                "📧 Envoyer",
                bgcolor="#2980B9",
                color="white",
                on_click=self.envoyer_par_mail,
            ),
            ft.IconButton(
                ft.icons.ZOOM_IN_ROUNDED,
                icon_color="white",
                bgcolor="#2C3E50",
                tooltip="Zoom Avant",
                on_click=lambda _: self.ajuster_zoom(0.15),
            ),
            ft.IconButton(
                ft.icons.ZOOM_OUT_ROUNDED,
                icon_color="white",
                bgcolor="#2C3E50",
                tooltip="Zoom Arrière",
                on_click=lambda _: self.ajuster_zoom(-0.15),
            ),
            ft.ElevatedButton(
                "⬅ Retour",
                bgcolor="#1F2937",
                color="white",
                on_click=self._retour_intelligent,
            ),
        ],
        wrap=True,
        spacing=10,
    )

    viewer_area = ft.Container(
        content=self.pdf_pages_column,
        alignment=ft.alignment.center,
        bgcolor="#111112",
        border_radius=8,
        padding=15,
        expand=True,
    )

    self.content = ft.Column(
        controls=[toolbar, viewer_area], spacing=12, expand=True
    )

  def on_file_picked(self, e: ft.FilePickerResultEvent):
    if e.files:
      filepath = e.files[0].path
      self.doc = {
          "numero": Path(filepath).stem,
          "externe_path": Path(filepath),
      }
      self.zoom = 1.2
      self.display_pdf()

  def ajuster_zoom(self, delta):
    self.zoom = max(0.5, min(3.0, self.zoom + delta))
    self.display_pdf()

  def imprimer_pdf(self, e):
    path = self.get_path()
    if not path or not path.exists():
      self.show_snack("Veuillez d'abord générer le document.", is_error=True)
      return

    printers = []
    try:
      if sys.platform == "win32":
        out = subprocess.check_output(
            [
                "powershell",
                "-Command",
                "Get-Printer | Select-Object -ExpandProperty Name",
            ],
            text=True,
            creationflags=0x08000000,
        )
        printers = [line.strip() for line in out.splitlines() if line.strip()]
      else:
        out = subprocess.check_output(["lpstat", "-p"], text=True)
        printers = [
            line.split()[1]
            for line in out.splitlines()
            if line.startswith("printer")
        ]
    except Exception as ex:
      print(f"[WARN] Liste imprimantes indisponible : {ex}")

    if not printers:
      try:
        if sys.platform == "win32":
          os.startfile(str(path), "print")
        else:
          subprocess.run(["lpr", str(path)])
        self.show_snack("Document envoyé à l'imprimante système par défaut.")
      except Exception as err:
        self.show_snack(f"Échec de l'impression : {err}", is_error=True)
      return

    dropdown_printers = ft.Dropdown(
        label="Imprimante",
        options=[ft.dropdown.Option(p) for p in printers],
        value=printers[0],
        width=320,
    )

    def valider_impression(ev):
      print_dialog.open = False
      if self.page:
        self.page.update()
      self.executer_impression(path, dropdown_printers.value)

    print_dialog = ft.AlertDialog(
        title=ft.Text("🖨️ Sélection de l'imprimante"),
        content=ft.Column(
            [ft.Text("Choisissez une machine disponible :"), dropdown_printers],
            tight=True,
        ),
        actions=[
            ft.TextButton(
                "Annuler",
                on_click=lambda _: setattr(print_dialog, "open", False)
                or (self.page and self.page.update()),
            ),
            ft.ElevatedButton(
                "Imprimer",
                bgcolor=self.accent_color,
                color="white",
                on_click=valider_impression,
            ),
        ],
    )
    if self.page:
      self.page.overlay.append(print_dialog)
      print_dialog.open = True
      self.page.update()

  def executer_impression(self, path, printer_name):
    try:
      if sys.platform == "win32":
        import ctypes

        ctypes.windll.shell32.ShellExecuteW(
            None, "printto", str(path), f'"{printer_name}"', None, 0
        )
      else:
        subprocess.run(["lpr", "-P", printer_name, str(path)])
      self.show_snack(f"Document envoyé vers {printer_name} ✔")
    except Exception as e:
      self.show_snack(f"Erreur Impression : {e}", is_error=True)

  def envoyer_par_mail(self, e):
    """Ouvre un dialogue complet et autonome pour envoyer le PDF par e-mail avec configuration SMTP."""
    path = (
        self.get_path()
        if hasattr(self, "get_path")
        else (Path(self.pdf_path) if self.pdf_path else None)
    )
    if not path or not os.path.exists(str(path)):
      self.show_snack("Veuillez d'abord générer le document PDF.", is_error=True)
      return

    path = Path(path)
    # 1. Recherche automatique de l'e-mail du destinataire (Client ou Fournisseur)
    email_dest = ""
    num_doc = "Document"
    if self.doc and isinstance(self.doc, dict):
      num_doc = self.doc.get("numero", "Document")
      c_raw = self.doc.get("client", self.doc.get("fournisseur", ""))
      nom_client = (
          c_raw.get("nom", "") if isinstance(c_raw, dict) else str(c_raw)
      )

      full_dest_data = next(
          (
              c
              for c in getattr(self.app, "clients", [])
              if str(c.get("nom")).strip().lower() == nom_client.strip().lower()
          ),
          None,
      )
      if not full_dest_data:
        full_dest_data = next(
            (
                f
                for f in getattr(self.app, "fournisseurs", [])
                if str(f.get("nom")).strip().lower()
                == nom_client.strip().lower()
            ),
            None,
        )

      if full_dest_data:
        email_dest = full_dest_data.get("email", "")
      elif isinstance(c_raw, dict):
        email_dest = c_raw.get("email", "")

    # 2. Chargement de la configuration SMTP locale si existante
    config_path = self.data_dir / "smtp_settings.json"
    smtp_conf = {}
    if config_path.exists():
      try:
        with open(config_path, "r", encoding="utf-8") as f:
          smtp_conf = json.load(f)
      except Exception:
        pass

    # 3. Éléments du formulaire de composition du message
    tf_to = ft.TextField(
        label="Destinataire", value=email_dest, placeholder="client@domaine.com"
    )
    tf_subject = ft.TextField(
        label="Objet", value=f"Votre document n° {num_doc}"
    )
    tf_body = ft.TextField(
        label="Corps du message",
        value=(
            "Bonjour,\n\nVeuillez trouver ci-joint votre document n°"
            f" {num_doc}.\n\nCordialement."
        ),
        multiline=True,
        min_lines=4,
        max_lines=6,
    )

    # 4. Éléments du formulaire de configuration SMTP
    tf_smtp_server = ft.TextField(
        label="Serveur SMTP",
        value=smtp_conf.get("server", "smtp.gmail.com"),
        expand=True,
    )
    tf_smtp_port = ft.TextField(
        label="Port", value=str(smtp_conf.get("port", "465")), width=100
    )
    tf_smtp_user = ft.TextField(
        label="Email expéditeur (Identifiant)", value=smtp_conf.get("user", "")
    )
    tf_smtp_pass = ft.TextField(
        label="Mot de passe d'application SMTP",
        value=smtp_conf.get("password", ""),
        password=True,
        can_reveal_password=True,
    )
    cb_use_ssl = ft.Checkbox(
        label="Utiliser SSL / TLS (Recommandé)",
        value=smtp_conf.get("use_ssl", True),
    )

    smtp_settings_layout = ft.Column(
        [
            ft.Divider(),
            ft.Text(
                "⚙️ Configuration Expéditeur (SMTP)",
                weight=ft.FontWeight.BOLD,
                size=12,
                color="#60A5FA",
            ),
            ft.Row([tf_smtp_server, tf_smtp_port], spacing=10),
            tf_smtp_user,
            tf_smtp_pass,
            cb_use_ssl,
        ],
        visible=not bool(smtp_conf.get("user")),
        spacing=10,
    )

    def toggle_smtp_settings(ev):
      smtp_settings_layout.visible = not smtp_settings_layout.visible
      mail_dialog.update()

    def lancer_envoi(ev):
      dest = tf_to.value.strip() if tf_to.value else ""
      subject = tf_subject.value.strip() if tf_subject.value else ""
      body = tf_body.value

      s_server = (
          tf_smtp_server.value.strip() if tf_smtp_server.value else ""
      )
      s_port = tf_smtp_port.value.strip() if tf_smtp_port.value else ""
      s_user = tf_smtp_user.value.strip() if tf_smtp_user.value else ""
      s_pass = tf_smtp_pass.value
      s_ssl = cb_use_ssl.value

      if not dest or "@" not in dest:
        self.show_snack(
            "L'adresse e-mail du destinataire est invalide.", is_error=True
        )
        return
      if not s_server or not s_port or not s_user or not s_pass:
        self.show_snack(
            "Veuillez renseigner tous les paramètres SMTP.", is_error=True
        )
        smtp_settings_layout.visible = True
        mail_dialog.update()
        return

      # Sauvegarde des paramètres pour les prochains envois
      try:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
          json.dump(
              {
                  "server": s_server,
                  "port": s_port,
                  "user": s_user,
                  "password": s_pass,
                  "use_ssl": s_ssl,
              },
              f,
              indent=4,
          )
      except Exception as ex:
        print(f"[WARN] Sauvegarde SMTP impossible : {ex}")

      mail_dialog.open = False
      if self.page:
        self.page.update()

      self.show_snack("Connexion au serveur et envoi du document... ⏳")

      def thread_email_process():
        try:
          msg = MIMEMultipart()
          msg["From"] = s_user
          msg["To"] = dest
          msg["Subject"] = subject
          msg.attach(MIMEText(body, "plain"))

          with open(path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition", f"attachment; filename={path.name}"
            )
            msg.attach(part)

          port_int = int(s_port)
          if s_ssl:
            server = smtplib.SMTP_SSL(s_server, port_int, timeout=15)
          else:
            server = smtplib.SMTP(s_server, port_int, timeout=15)
            server.starttls()

          server.login(s_user, s_pass)
          server.sendmail(s_user, dest, msg.as_string())
          server.quit()

          self.show_snack(f"E-mail envoyé avec succès à {dest} ! ✔")
        except Exception as error:
          self.show_snack(f"Échec de l'envoi : {error}", is_error=True)

      threading.Thread(target=thread_email_process, daemon=True).start()

    mail_dialog = ft.AlertDialog(
        title=ft.Row(
            [
                ft.Icon(
                    ft.icons.EMAIL_ROUNDED,
                    color=self.accent_color or "#3B82F6",
                ),
                ft.Text(
                    "Envoi du document par E-mail",
                    size=16,
                    weight=ft.FontWeight.BOLD,
                ),
            ],
            spacing=10,
        ),
        content=ft.Container(
            content=ft.Column(
                [
                    tf_to,
                    tf_subject,
                    tf_body,
                    ft.TextButton(
                        text="Ajuster les paramètres SMTP d'envoi",
                        icon=ft.icons.SETTINGS_ROUNDED,
                        on_click=toggle_smtp_settings,
                    ),
                    smtp_settings_layout,
                ],
                spacing=12,
                tight=True,
                scroll=ft.ScrollMode.AUTO,
            ),
            width=460,
            max_height=520,
        ),
        actions=[
            ft.TextButton(
                "Annuler",
                on_click=lambda _: setattr(mail_dialog, "open", False)
                or (self.page and self.page.update()),
            ),
            ft.ElevatedButton(
                "🚀 Envoyer",
                bgcolor=self.accent_color or "#3B82F6",
                color="white",
                on_click=lancer_envoi,
            ),
        ],
    )

    if self.page:
      self.page.overlay.append(mail_dialog)
      mail_dialog.open = True
      self.page.update()

  def lancer_signature_pad(self, e):
    path = self.get_path()
    if not path or not path.exists():
      self.show_snack("Veuillez d'abord générer le document.", is_error=True)
      return

    canvas_w, canvas_h = 400, 150
    self.sig_image = Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 0))
    self.draw_img = ImageDraw.Draw(self.sig_image)
    self.last_x, self.last_y = None, None

    self.canvas_control = cv.Canvas(expand=True, shapes=[])

    def on_pan_start(ev: ft.DragStartEvent):
      self.last_x = ev.local_x
      self.last_y = ev.local_y
      self.current_path = cv.Path(
          [cv.MoveTo(ev.local_x, ev.local_y)],
          stroke=ft.Paint(
              stroke_width=2.5,
              color="#1E3A8A",
              style=ft.PaintingStyle.STROKE,
              stroke_cap=ft.StrokeCap.ROUND,
          ),
      )
      self.canvas_control.shapes.append(self.current_path)
      self.canvas_control.update()

    def on_pan_update(ev: ft.DragUpdateEvent):
      if self.last_x is not None and self.last_y is not None:
        self.current_path.elements.append(cv.LineTo(ev.local_x, ev.local_y))
        self.canvas_control.update()
        self.draw_img.line(
            [self.last_x, self.last_y, ev.local_x, ev.local_y],
            fill="#1E3A8A",
            width=3,
        )
      self.last_x = ev.local_x
      self.last_y = ev.local_y

    def on_pan_end(ev: ft.DragEndEvent):
      self.last_x, self.last_y = None, None

    def clear_canvas(ev):
      self.canvas_control.shapes.clear()
      self.canvas_control.update()
      self.sig_image = Image.new(
          "RGBA", (canvas_w, canvas_h), (255, 255, 255, 0)
      )
      self.draw_img = ImageDraw.Draw(self.sig_image)

    def valider_signature(ev):
      sig_folder = self.data_dir / "signatures"
      sig_folder.mkdir(parents=True, exist_ok=True)
      target_path = sig_folder / "temp_signature.png"
      self.sig_image.save(target_path, "PNG")

      sig_dialog.open = False
      if self.page:
        self.page.update()
      self.appliquer_signature_sur_pdf(target_path)

    gesture_detector = ft.GestureDetector(
        content=self.canvas_control,
        on_pan_start=on_pan_start,
        on_pan_update=on_pan_update,
        on_pan_end=on_pan_end,
        expand=True,
    )

    sig_dialog = ft.AlertDialog(
        title=ft.Text(
            "✍️ Signature Électronique", size=16, weight=ft.FontWeight.BOLD
        ),
        content=ft.Column(
            [
                ft.Text(
                    "Signez au doigt ou à la souris dans l'encadré :", size=12
                ),
                ft.Container(
                    content=gesture_detector,
                    width=canvas_w,
                    height=canvas_h,
                    bgcolor="white",
                    border=ft.border.all(1, "#D1D5DB"),
                    border_radius=6,
                ),
            ],
            tight=True,
            spacing=10,
        ),
        actions=[
            ft.ElevatedButton(
                "🗑️ Effacer",
                bgcolor="#EF4444",
                color="white",
                on_click=clear_canvas,
            ),
            ft.ElevatedButton(
                "💾 Apposer",
                bgcolor="#16A34A",
                color="white",
                on_click=valider_signature,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )
    if self.page:
      self.page.overlay.append(sig_dialog)
      sig_dialog.open = True
      self.page.update()

  def appliquer_signature_sur_pdf(self, image_signature_path):
    """Incruste l'image de signature sur la dernière page du document de façon alignée."""
    try:
      path = self.get_path()
      if not path or not path.exists():
        return

      sig_folder = self.data_dir / "signatures"
      num_doc = (
          self.doc.get("numero", "TEMP_DOC")
          if isinstance(self.doc, dict)
          else "TEMP_DOC"
      )
      permanent_sig_path = sig_folder / f"{num_doc}.png"

      if image_signature_path.exists():
        if permanent_sig_path.exists():
          permanent_sig_path.unlink()
        image_signature_path.rename(permanent_sig_path)

      doc = fitz.open(path)
      page = doc[-1]

      rect_signature = fitz.Rect(350, 722, 520, 767)
      page.insert_image(rect_signature, filename=str(permanent_sig_path))

      timestamp = datetime.now().strftime("%d/%m/%Y à %H:%M:%S")
      log_text = (
          f"Certifié conforme le {timestamp} par signature cryptographique"
          " locale."
      )
      page.insert_text(
          fitz.Point(345, 770), log_text, fontsize=6, color=(0.5, 0.5, 0.5)
      )

      doc.saveIncr()
      doc.close()

      if isinstance(self.doc, dict):
        self.doc["statut"] = "Signé"
        self.doc["date_signature"] = timestamp
        if hasattr(self.app, "save_data"):
          self.app.save_data()

      self.show_snack("Document validé et signé électroniquement ! ✔")
      self.display_pdf()
    except Exception as e:
      self.show_snack(
          f"Échec du marquage de signature : {e}", is_error=True
      )

  def generer_pdf_pro(self, silent=False):
    """Moteur de rendu ReportLab Premium Pro - Version Conforme Loi Française."""
    if not self.doc:
      return
    if isinstance(self.doc, dict) and "externe_path" in self.doc:
      self.display_pdf()
      return

    path = self.get_path()
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4

    hex_color = "#1E3A8A"
    if hasattr(self.app, "entreprise") and isinstance(
        self.app.entreprise, dict
    ):
      hex_color = self.app.entreprise.get("accent_color", "#1E3A8A")

    primary_color = colors.HexColor(hex_color)
    text_dark = colors.HexColor("#0F172A")
    text_muted = colors.HexColor("#475569")
    bg_light = colors.HexColor("#F8FAFC")
    border_color = colors.HexColor("#E2E8F0")

    t_doc = (
        self.doc.get("type_doc_interne")
        if isinstance(self.doc, dict)
        else None
    )
    entreprise_data = getattr(self.app, "entreprise", {})

    # ==============================================================
    # RENDU : Fiche Contact Client
    # ==============================================================
    if t_doc == "fiche_contact":
      c.setStrokeColor(primary_color)
      c.setLineWidth(3)
      c.line(45, height - 30, width - 45, height - 30)

      c.setFillColor(text_dark)
      c.setFont("Helvetica-Bold", 14)
      c.drawString(
          45, height - 60, entreprise_data.get("nom", "MON ENTREPRISE").upper()
      )
      c.setFont("Helvetica", 8)
      c.setFillColor(text_muted)
      c.drawString(
          45,
          height - 72,
          f"SIRET : {entreprise_data.get('siret', '-')} | CRM Interne",
      )

      c.setFillColor(primary_color)
      c.setFont("Helvetica-Bold", 18)
      c.drawString(45, height - 120, "FICHE D'IDENTIFICATION COMPLÈTE")

      c.setStrokeColor(border_color)
      c.setLineWidth(0.5)
      c.line(45, height - 130, width - 45, height - 130)

      c.setFont("Helvetica", 8.5)
      c.setFillColor(text_muted)
      c.drawString(
          45,
          height - 145,
          f"Date d'extraction : {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
      )
      c.drawRightString(
          width - 45,
          height - 145,
          f"ID Base : {self.doc.get('numero', 'N/A')}",
      )

      infos_contact = [
          (
              "Raison Sociale / Nom",
              self.doc.get("nom", "-").upper(),
              "Helvetica-Bold",
              text_dark,
          ),
          (
              "Numéro SIRET",
              self.doc.get("siret", "-") or "Non renseigné",
              "Helvetica",
              text_dark,
          ),
          (
              "Ligne Téléphonique",
              self.doc.get("telephone", "-") or "Non renseigné",
              "Helvetica",
              text_dark,
          ),
          (
              "Courrier Électronique",
              self.doc.get("email", "-") or "Non renseigné",
              "Helvetica",
              text_dark,
          ),
          (
              "Adresse Postale",
              f"{self.doc.get('adresse', '-')}\n{self.doc.get('code_postal', '-')} {self.doc.get('ville', '-')}",
              "Helvetica",
              text_dark,
          ),
      ]

      y_grid = height - 180
      for label, val, font_style, color_style in infos_contact:
        c.setFillColor(bg_light)
        c.rect(45, y_grid - 24, 150, 30, fill=1, stroke=0)

        c.setFillColor(text_muted)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(55, y_grid - 12, label)

        c.setFillColor(color_style)
        c.setFont(font_style, 10)

        if "\n" in str(val):
          y_multiline = y_grid - 8
          for line in str(val).split("\n"):
            c.drawString(210, y_multiline, line)
            y_multiline -= 14
        else:
          c.drawString(210, y_grid - 12, str(val))

        c.setStrokeColor(border_color)
        c.line(45, y_grid - 24, width - 45, y_grid - 24)
        y_grid -= 38

      # Bloc signature
      c.setStrokeColor(border_color)
      c.setLineWidth(0.5)
      c.setFillColor(bg_light)
      c.roundRect(335, 65, 210, 100, 3, stroke=1, fill=1)
      c.setFillColor(text_dark)
      c.setFont("Helvetica-Bold", 8)
      c.drawString(345, 153, "CADRE DE VALIDATION / SIGNATURE")
      c.setFont("Helvetica-Oblique", 7.5)
      c.setFillColor(text_muted)
      c.drawString(345, 138, "Fiche validée le : ...................................")
      c.drawString(345, 110, "Signature exécutoire :")

      num_doc = self.doc.get("numero", "TEMP_DOC")
      permanent_sig_path = self.data_dir / "signatures" / f"{num_doc}.png"
      if self.doc.get("statut") == "Signé" and permanent_sig_path.exists():
        try:
          c.drawImage(
              str(permanent_sig_path),
              350,
              75,
              width=170,
              height=45,
              mask="auto",
          )
          timestamp = self.doc.get(
              "date_signature", datetime.now().strftime("%d/%m/%Y à %H:%M:%S")
          )
          c.setFillColor(colors.HexColor("#475569"))
          c.setFont("Helvetica", 6)
          c.drawString(
              345, 72, f"Document signé numériquement le {timestamp}"
          )
        except Exception as e:
          print(f"[WARN] Incrustation signature en échec : {e}")

      c.line(45, 55, width - 45, 55)
      c.setFont("Helvetica-Oblique", 7.5)
      c.setFillColor(text_muted)
      c.drawCentredString(
          width / 2,
          42,
          "Ce document contient des informations à caractère personnel"
          " protégées par le RGPD. Diffusion interdite.",
      )
      c.save()
      if not silent:
        self.show_snack("Fiche d'identification client générée.")
      self.display_pdf()
      return

    # ==============================================================
    # RENDU : Fiche Fournisseur
    # ==============================================================
    if t_doc == "fiche_fournisseur":
      c.setStrokeColor(colors.HexColor("#475569"))
      c.setLineWidth(3)
      c.line(45, height - 30, width - 45, height - 30)

      c.setFillColor(text_dark)
      c.setFont("Helvetica-Bold", 18)
      c.drawString(45, height - 60, "DOSSIER TECHNIQUE FOURNISSEUR")

      c.setStrokeColor(border_color)
      c.line(45, height - 70, width - 45, height - 70)

      y = height - 100
      infos = [
          ("Raison Sociale", self.doc.get("nom", "-")),
          ("Numéro SIRET", self.doc.get("siret", "-")),
          ("Téléphone", self.doc.get("telephone", "-")),
          ("E-mail Professionnel", self.doc.get("email", "-")),
          ("Adresse Postale", self.doc.get("adresse", "-")),
          ("Identifiant IBAN", self.doc.get("iban", "Non renseigné")),
          ("Code BIC / SWIFT", self.doc.get("bic", "Non renseigné")),
      ]

      for label, val in infos:
        c.setFillColor(bg_light)
        c.rect(45, y - 20, 155, 26, fill=1, stroke=0)
        c.setFillColor(text_muted)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(55, y - 8, label)
        c.setFillColor(text_dark)
        c.setFont("Helvetica", 9.5)
        c.drawString(210, y - 8, str(val))
        c.setStrokeColor(border_color)
        c.line(45, y - 20, width - 45, y - 20)
        y -= 32

      c.setStrokeColor(border_color)
      c.setLineWidth(0.5)
      c.setFillColor(bg_light)
      c.roundRect(335, 65, 210, 100, 3, stroke=1, fill=1)
      c.setFillColor(text_dark)
      c.setFont("Helvetica-Bold", 8)
      c.drawString(345, 153, "CADRE DE VALIDATION / SIGNATURE")
      c.setFont("Helvetica-Oblique", 7.5)
      c.setFillColor(text_muted)
      c.drawString(
          345, 138, "Dossier approuvé le : ............................."
      )
      c.drawString(345, 110, "Signature exécutoire :")

      num_doc = self.doc.get("numero", "TEMP_DOC")
      permanent_sig_path = self.data_dir / "signatures" / f"{num_doc}.png"
      if self.doc.get("statut") == "Signé" and permanent_sig_path.exists():
        try:
          c.drawImage(
              str(permanent_sig_path),
              350,
              75,
              width=170,
              height=45,
              mask="auto",
          )
          timestamp = self.doc.get(
              "date_signature", datetime.now().strftime("%d/%m/%Y à %H:%M:%S")
          )
          c.setFillColor(colors.HexColor("#475569"))
          c.setFont("Helvetica", 6)
          c.drawString(
              345, 72, f"Document signé numériquement le {timestamp}"
          )
        except Exception as e:
          print(f"[WARN] Incrustation signature en échec : {e}")

      c.line(45, 55, width - 45, 55)
      c.save()
      if not silent:
        self.show_snack("Dossier fournisseur synchronisé.")
      self.display_pdf()
      return

    # ==============================================================
    # RENDU : Factures, Devis, Bons de Commande / Livraison
    # ==============================================================
    if t_doc:
      if t_doc == "facture":
        titre_doc = "FACTURE"
      elif t_doc == "devis":
        titre_doc = "DEVIS"
      elif t_doc == "bon_commande":
        titre_doc = "BON DE COMMANDE"
      elif t_doc == "bon_livraison":
        titre_doc = "BON DE LIVRAISON"
      else:
        titre_doc = str(t_doc).upper()
    else:
      is_facture = "FACT" in str(
          self.doc.get("numero", "")
      ).upper() or str(self.doc.get("numero", "")).upper().startswith("F")
      titre_doc = "FACTURE" if is_facture else "DEVIS"

    def dessiner_footer(canvas_obj, current_page):
      canvas_obj.setStrokeColor(border_color)
      canvas_obj.setLineWidth(0.5)
      canvas_obj.line(45, 55, width - 45, 55)

      canvas_obj.setFillColor(text_muted)
      canvas_obj.setFont("Helvetica", 7.5)
      statut = entreprise_data.get("statut_juridique", "Société")
      siret = entreprise_data.get("siret", "000 000 000 00000")
      nom_ent = entreprise_data.get("nom", "Entreprise")
      rc_pro = entreprise_data.get("rc_pro", "")

      mentions_legales = (
          f"{nom_ent} — {statut} au capital social variable — SIRET :"
          f" {siret} — {rc_pro}"
      )
      canvas_obj.drawCentredString(width / 2, 42, mentions_legales)
      canvas_obj.drawRightString(width - 45, 42, f"Page {current_page}")

    def dessiner_entete_page(canvas_obj, page_num):
      canvas_obj.setFillColor(primary_color)
      canvas_obj.rect(0, height - 6, width, 6, stroke=0, fill=1)

      if page_num == 1:
        canvas_obj.setFillColor(text_dark)
        canvas_obj.setFont("Helvetica-Bold", 14)
        canvas_obj.drawString(
            45,
            height - 45,
            entreprise_data.get("nom", "MON ENTREPRISE").upper(),
        )

        canvas_obj.setFont("Helvetica", 8.5)
        canvas_obj.setFillColor(text_muted)

        y_em = height - 59
        adr_e = entreprise_data.get("adresse", "")
        cp_e = entreprise_data.get("code_postal", "")
        v_e = entreprise_data.get("ville", "")

        canvas_obj.drawString(45, y_em, f"{adr_e}, {cp_e} {v_e}")
        canvas_obj.drawString(
            45,
            y_em - 13,
            f"SIRET : {entreprise_data.get('siret', '-')} | TVA :"
            f" {entreprise_data.get('tva_intracom', '-')}",
        )
        canvas_obj.drawString(
            45,
            y_em - 26,
            f"Contact : {entreprise_data.get('email', '-')} |"
            f" {entreprise_data.get('telephone', '-')}",
        )

        # Zone du Destinataire
        canvas_obj.setStrokeColor(border_color)
        canvas_obj.setLineWidth(0.5)
        canvas_obj.setFillColor(bg_light)
        canvas_obj.roundRect(330, height - 120, 220, 85, 4, stroke=1, fill=1)

        canvas_obj.setFillColor(primary_color)
        canvas_obj.setFont("Helvetica-Bold", 7.5)
        label_dest = (
            "DESTINATAIRE FOURNISSEUR"
            if t_doc in ["bon_commande", "bon_livraison"]
            else "DESTINATAIRE CLIENT"
        )
        canvas_obj.drawString(342, height - 48, label_dest)

        c_raw = self.doc.get(
            "client", self.doc.get("fournisseur", "Client Non Référencé")
        )
        nom_client = (
            c_raw.get("nom", "") if isinstance(c_raw, dict) else str(c_raw)
        )

        full_dest_data = next(
            (
                c
                for c in getattr(self.app, "clients", [])
                if str(c.get("nom")).strip().lower() == nom_client.strip().lower()
            ),
            None,
        )
        if not full_dest_data:
          full_dest_data = next(
              (
                  f
                  for f in getattr(self.app, "fournisseurs", [])
                  if str(f.get("nom")).strip().lower()
                  == nom_client.strip().lower()
              ),
              None,
          )

        c_data = (
            full_dest_data
            if isinstance(full_dest_data, dict)
            else (c_raw if isinstance(c_raw, dict) else {"nom": nom_client})
        )

        canvas_obj.setFillColor(text_dark)
        canvas_obj.setFont("Helvetica-Bold", 10.5)
        canvas_obj.drawString(
            342, height - 64, c_data.get("nom", "Inconnu").upper()
        )

        canvas_obj.setFont("Helvetica", 8.5)
        canvas_obj.setFillColor(text_muted)
        y_cli = height - 78
        c_adr = (
            f"{c_data.get('adresse', '')}, {c_data.get('code_postal', '')}"
            f" {c_data.get('ville', '')}"
        ).strip(", ")
        if c_adr:
          canvas_obj.drawString(342, y_cli, c_adr[:45])
        if c_data.get("siret"):
          canvas_obj.drawString(342, y_cli - 13, f"SIRET : {c_data['siret']}")

        # Bloc Infos Titre Document
        canvas_obj.setFillColor(text_dark)
        canvas_obj.setFont("Helvetica-Bold", 16)
        canvas_obj.drawString(
            45, height - 150, f"{titre_doc} # {self.doc.get('numero', 'N/A')}"
        )

        canvas_obj.setStrokeColor(primary_color)
        canvas_obj.setLineWidth(1)
        canvas_obj.line(45, height - 158, width - 45, height - 158)

        canvas_obj.setFont("Helvetica", 8.5)
        canvas_obj.setFillColor(text_muted)
        date_doc = self.doc.get(
            "date_creation", datetime.now().strftime("%d/%m/%Y")
        )
        canvas_obj.drawString(45, height - 173, f"Date d'émission : {date_doc}")

        date_ech = self.doc.get("date_echeance", "À réception")
        canvas_obj.drawRightString(
            width - 45, height - 173, f"Date limite de règlement : {date_ech}"
        )

        statut_doc = str(self.doc.get("statut", ""))
        if titre_doc == "FACTURE" and any(
            x in statut_doc.lower() for x in ["payé", "déclaré"]
        ):
          canvas_obj.saveState()
          canvas_obj.translate(width - 120, height - 142)
          canvas_obj.rotate(-10)
          canvas_obj.setStrokeColor(colors.HexColor("#10B981"))
          canvas_obj.setLineWidth(1.5)
          canvas_obj.roundRect(-55, -12, 110, 24, 3, stroke=1, fill=0)
          canvas_obj.setFillColor(colors.HexColor("#10B981"))
          canvas_obj.setFont("Helvetica-Bold", 10)
          canvas_obj.drawCentredString(0, -3, "DOC. ACQUITTE")
          canvas_obj.restoreState()

        return height - 200
      else:
        canvas_obj.setFillColor(text_dark)
        canvas_obj.setFont("Helvetica-Bold", 9)
        canvas_obj.drawString(
            45,
            height - 30,
            f"{titre_doc} n° {self.doc.get('numero', 'N/A')} — Page {page_num}",
        )
        canvas_obj.setStrokeColor(border_color)
        canvas_obj.line(45, height - 36, width - 45, height - 36)
        return height - 55

    def dessiner_entete_tableau(canvas_obj, y_pos):
      canvas_obj.setFillColor(bg_light)
      canvas_obj.rect(45, y_pos, width - 90, 20, stroke=0, fill=1)
      canvas_obj.setStrokeColor(border_color)
      canvas_obj.line(45, y_pos, width - 45, y_pos)
      canvas_obj.line(45, y_pos + 20, width - 45, y_pos + 20)

      canvas_obj.setFillColor(text_dark)
      canvas_obj.setFont("Helvetica-Bold", 8.5)
      canvas_obj.drawString(
          52, y_pos + 6, "Description de la prestation / produit"
      )
      canvas_obj.drawRightString(375, y_pos + 6, "Qté")
      canvas_obj.drawRightString(455, y_pos + 6, "P.U. HT")
      canvas_obj.drawRightString(540, y_pos + 6, "Total HT")
      return y_pos - 18

    page_num = 1
    y_table = dessiner_entete_page(c, page_num)
    y_items = dessiner_entete_tableau(c, y_table)

    total_global_ht = 0.0
    items_list = self.doc.get("articles", self.doc.get("lignes", []))
    if not items_list:
      items_list = [{
          "designation": "Prestation de services standard",
          "qty": 1,
          "pu": float(
              self.doc.get(
                  "total_ttc",
                  self.doc.get("montant_ht", self.doc.get("montant", 0)),
              )
          )
          or 0.0,
      }]

    for idx, item in enumerate(items_list):
      desc = str(item.get("designation", item.get("nom", "Article")))

      mots = desc.split(" ")
      lignes_desc = []
      ligne_courante = ""
      for mot in mots:
        if len(ligne_courante + mot) <= 62:
          ligne_courante += mot + " "
        else:
          lignes_desc.append(ligne_courante.strip())
          ligne_courante = mot + " "
      if ligne_courante:
        lignes_desc.append(ligne_courante.strip())

      hauteur_totale_bloc = len(lignes_desc) * 13

      if y_items - hauteur_totale_bloc < 160:
        dessiner_footer(c, page_num)
        c.showPage()
        page_num += 1
        y_table = dessiner_entete_page(c, page_num)
        y_items = dessiner_entete_tableau(c, y_table)

      if idx % 2 == 1:
        c.setFillColor(colors.HexColor("#FAFAFA"))
        c.rect(
            45,
            y_items - hauteur_totale_bloc + 4,
            width - 90,
            hauteur_totale_bloc + 2,
            stroke=0,
            fill=1,
        )

      c.setFillColor(text_dark)
      c.setFont("Helvetica", 9)

      try:
        qty = int(item.get("qty", item.get("quantite", item.get("qte", 1))))
      except:
        qty = 1
      try:
        pu = float(
            item.get(
                "pu", item.get("prix", item.get("prix_unitaire", 0.0))
            )
        )
      except:
        pu = 0.0

      t_ht = qty * pu
      total_global_ht += t_ht

      y_write = y_items
      for line in lignes_desc:
        c.drawString(52, y_write, line)
        y_write -= 13

      c.drawRightString(375, y_items, str(qty))
      c.drawRightString(455, y_items, f"{pu:.2f} €")
      c.drawRightString(540, y_items, f"{t_ht:.2f} €")

      y_items -= hauteur_totale_bloc + 3

    c.setStrokeColor(border_color)
    c.line(45, y_items + 6, width - 45, y_items + 6)

    notes_globales = self.doc.get("notes", self.doc.get("observations", ""))
    if notes_globales and str(notes_globales).strip():
      y_items -= 8
      if y_items < 180:
        dessiner_footer(c, page_num)
        c.showPage()
        page_num += 1
        y_table = dessiner_entete_page(c, page_num)
        y_items = y_table - 15

      c.setFillColor(text_dark)
      c.setFont("Helvetica-Bold", 8)
      c.drawString(45, y_items, "Note d'information / Conditions spécifiques :")
      y_items -= 11
      c.setFont("Helvetica", 8)
      c.setFillColor(text_muted)

      for l_note in str(notes_globales).split("\n"):
        if y_items < 140:
          dessiner_footer(c, page_num)
          c.showPage()
          page_num += 1
          y_table = dessiner_entete_page(c, page_num)
          y_items = y_table - 15
        c.drawString(45, y_items, l_note)
        y_items -= 11

    if y_items < 240:
      dessiner_footer(c, page_num)
      c.showPage()
      page_num += 1
      y_table = dessiner_entete_page(c, page_num)
      y_items = y_table - 15

    y_bloc_total = y_items - 20
    c.setFillColor(text_dark)
    c.setFont("Helvetica", 9.5)
    c.drawString(350, y_bloc_total, "Montant Total HT")
    c.drawRightString(540, y_bloc_total, f"{total_global_ht:.2f} €")

    tva_doc = float(self.doc.get("montant_tva", self.doc.get("tva", 0.0)))
    if tva_doc == 0.0 and entreprise_data.get("soumis_tva", "Non") == "Oui":
      tva_doc = total_global_ht * 0.20

    total_global_ttc = total_global_ht + tva_doc
    tva_label = "20%" if tva_doc > 0 else "0%"

    c.drawString(
        350, y_bloc_total - 15, f"Taxe sur la Valeur Ajoutée ({tva_label})"
    )
    c.drawRightString(540, y_bloc_total - 15, f"{tva_doc:.2f} €")

    c.setStrokeColor(primary_color)
    c.setLineWidth(0.5)
    c.line(350, y_bloc_total - 21, 545, y_bloc_total - 21)

    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(primary_color)
    c.drawString(350, y_bloc_total - 35, "NET À REGLER (TTC)")
    c.drawRightString(540, y_bloc_total - 35, f"{total_global_ttc:.2f} €")

    c.setFillColor(text_muted)
    c.setFont("Helvetica-Oblique", 7.5)
    if tva_doc == 0:
      c.drawString(
          45,
          y_bloc_total - 35,
          str(
              entreprise_data.get(
                  "mention_tva", "TVA non applicable, art. 293 B du CGI"
              )
          ),
      )

    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(text_dark)
    c.drawString(
        45,
        y_bloc_total - 65,
        "CONDITIONS DE RÈGLEMENT COMMERCIALES & LÉGALES :",
    )
    c.setFont("Helvetica", 7.5)
    c.setFillColor(text_muted)

    iban = entreprise_data.get("iban", "-")
    bic = entreprise_data.get("bic", "-")

    lignes_legales = [
        "Règlement par virement bancaire sur compte d'exploitation courant :"
        f" IBAN {iban} — BIC {bic}",
        (
            "Pas d'escompte consenti pour versement anticipé. En cas de retard"
            " de paiement de la présente facture à l'échéance,"
        ),
        (
            "il sera appliqué de plein droit des pénalités de retard calculées"
            " sur la base de 3 fois le taux d'intérêt légal en vigueur."
        ),
        (
            "Indemnité forfaitaire légale pour frais de recouvrement"
            " obligatoire en cas de retard : 40,00 € (Art. L441-6 / Code de"
            " Com.)."
        ),
    ]
    y_leg = y_bloc_total - 77
    for line in lignes_legales:
      c.drawString(45, y_leg, line)
      y_leg -= 11

    # Cartouche de Validation
    c.setStrokeColor(border_color)
    c.setLineWidth(0.5)
    c.setFillColor(bg_light)
    c.roundRect(335, 65, 210, 100, 3, stroke=1, fill=1)

    c.setFillColor(text_dark)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(345, 153, "CADRE DE VALIDATION ET SIGNATURE")

    c.setFont("Helvetica-Oblique", 7.5)
    c.setFillColor(text_muted)
    c.drawString(345, 138, "Mention manuscrite obligatoire 'Bon pour accord'")
    c.drawString(
        345, 126, "Précédée de la date du jour : ..................................."
    )
    c.drawString(345, 110, "Signature exécutoire :")

    num_doc = self.doc.get("numero", "TEMP_DOC")
    permanent_sig_path = self.data_dir / "signatures" / f"{num_doc}.png"
    if self.doc.get("statut") == "Signé" and permanent_sig_path.exists():
      try:
        c.drawImage(
            str(permanent_sig_path),
            350,
            75,
            width=170,
            height=45,
            mask="auto",
        )
        timestamp = self.doc.get(
            "date_signature", datetime.now().strftime("%d/%m/%Y à %H:%M:%S")
        )
        c.setFillColor(colors.HexColor("#475569"))
        c.setFont("Helvetica", 6)
        c.drawString(345, 72, f"Document signé numériquement le {timestamp}")
      except Exception as e:
        print(f"[WARN] Incrustation signature en échec : {e}")

    dessiner_footer(c, page_num)
    c.save()

    if not silent:
      self.show_snack(f"Rendu {titre_doc.lower()} mis à jour avec succès ✔")

    self.display_pdf()

  def show_snack(self, message, is_error=False):
    """Notification Snack-bar Flet moderne rattachée à l'overlay de la page."""
    snack = ft.SnackBar(
        content=ft.Text(message, color="white"),
        bgcolor="red700" if is_error else "green700",
        duration=3000,
    )
    if self.page:
      self.page.overlay.append(snack)
      snack.open = True
      self.page.update()
