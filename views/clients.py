import os
import shutil
from pathlib import Path
import flet as ft


def safe_border(width=1, color="#2A2A32"):
    """Bordure universelle sécurisée compatible Desktop et Mobile."""
    side = ft.BorderSide(width, color)
    return ft.Border(top=side, right=side, bottom=side, left=side)


class ClientsView(ft.Container):
    """Vue Flet pour la gestion de la base clients et pièces jointes (Responsive)."""

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.expand = True
        self.padding = 10

        # États de contrôle
        self.editing_idx = None
        self.opened_docs_idx = None

        # FilePicker multiplateforme
        self.file_picker = ft.FilePicker()
        self.file_picker.on_result = self.on_file_picker_result

        # Couleur d'accentuation
        self.accent_color = "#2B719E"
        if hasattr(self.app, "entreprise") and isinstance(self.app.entreprise, dict):
            self.accent_color = self.app.entreprise.get("accent_color", "#2B719E")

        self.setup_ui()

    def did_mount(self):
        """Attache l'explorateur de fichiers au montage du composant."""
        page_obj = self.page or getattr(self.app, "page", None)
        if page_obj and self.file_picker not in page_obj.overlay:
            page_obj.overlay.append(self.file_picker)
            page_obj.update()
        self.refresh_client_list(force_update=False)

    def setup_ui(self):
        """Initialise l'interface utilisateur."""
        title = ft.Row([
            ft.IconButton(
                icon="arrow_back",
                tooltip="Retour",
                on_click=lambda e: self.app.navigate_to("Dashboard")
            ),
            ft.Text("👥 Répertoire Clients", size=20, weight=ft.FontWeight.BOLD)
        ])

        # --- FORMULAIRE (Gauche) ---
        self.lbl_form_title = ft.Text(
            "📝 Ajouter un nouveau client",
            size=14,
            weight=ft.FontWeight.BOLD,
            color=self.accent_color
        )

        self.fields = {}
        fields_config = [
            ("nom", "Nom / Raison Sociale *", "Ex: Entreprise Martin, Jean Dupont..."),
            ("contact_nom", "Nom du contact référent", "Ex: Alice Martin"),
            ("email", "E-mail", "Ex: contact@client.com"),
            ("telephone", "Téléphone", "Ex: 06 12 34 56 78"),
            ("adresse", "Adresse (Rue)", "Ex: 15 Rue des Lilas"),
            ("code_postal", "Code Postal", "Ex: 75001"),
            ("ville", "Ville", "Ex: Paris"),
            ("pays", "Pays", "Ex: France"),
            ("siret", "Numéro SIRET (Optionnel)", "Ex: 123 456 789 00012"),
            ("tva", "N° TVA Intracommunautaire", "Ex: FR 12 345678901")
        ]

        form_controls = [self.lbl_form_title]

        for key, label, placeholder in fields_config:
            entry = ft.TextField(
                label=label,
                hint_text=placeholder,
                bgcolor="#242426",
                text_size=12,
                border_radius=6,
                border_color="#3A3A3C",
                content_padding=10
            )
            self.fields[key] = entry
            form_controls.append(entry)

        self.btn_save = ft.ElevatedButton(
            content=ft.Text("💾 Enregistrer"),
            bgcolor="#15803D",
            color="white",
            height=38,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
            on_click=lambda e: self.valider_client()
        )
        self.btn_cancel = ft.OutlinedButton(
            content=ft.Text("🔄 Réinitialiser"),
            height=38,
            style=ft.ButtonStyle(color="white", shape=ft.RoundedRectangleBorder(radius=6)),
            on_click=lambda e: self.vider_champs()
        )

        form_controls.append(ft.Row([self.btn_save, self.btn_cancel], spacing=10))

        form_frame = ft.Container(
            content=ft.Column(controls=form_controls, spacing=8, scroll=ft.ScrollMode.AUTO),
            bgcolor="#1A1A1C",
            padding=15,
            border_radius=12,
            border=safe_border(1, "#2A2A32"),
            col={"sm": 12, "md": 4}
        )

        # --- LISTE DES CLIENTS (Droite) ---
        self.search_entry = ft.TextField(
            hint_text="🔍 Rechercher par nom, téléphone, email ou ville...",
            bgcolor="#1A1A1C",
            text_size=13,
            border_radius=6,
            border_color="#3A3A3C",
            on_change=lambda e: self.refresh_client_list()
        )

        self.list_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=10)

        list_container = ft.Container(
            content=self.list_column,
            bgcolor="#141416",
            padding=10,
            border_radius=12,
            border=safe_border(1, "#2A2A2E"),
            expand=True
        )

        right_frame = ft.Container(
            content=ft.Column(
                controls=[
                    self.search_entry,
                    ft.Text("Fiches clients enregistrées", size=12, weight=ft.FontWeight.BOLD, color="#AEAEB2"),
                    list_container
                ],
                expand=True
            ),
            col={"sm": 12, "md": 8}
        )

        self.main_layout = ft.ResponsiveRow(
            controls=[form_frame, right_frame],
            spacing=15,
            expand=True
        )

        self.content = ft.Column(
            controls=[title, self.main_layout],
            spacing=10,
            expand=True
        )

    def refresh_client_list(self, force_update=True):
        """Regénère dynamiquement l'affichage des fiches clients."""
        search_term = self.search_entry.value.lower().strip() if (hasattr(self, "search_entry") and self.search_entry.value) else ""
        self.list_column.controls.clear()

        clients_list = getattr(self.app, "clients", [])

        if not clients_list:
            self.list_column.controls.append(
                ft.Container(
                    content=ft.Text("Aucun client dans votre base de données.", size=13, italic=True, color="#636366"),
                    alignment=ft.alignment.center,
                    padding=30
                )
            )
            if force_update and self.page:
                self.page.update()
            return

        visible_clients = 0

        for idx, client in enumerate(clients_list):
            nom = str(client.get("nom", "")).lower()
            email = str(client.get("email", "")).lower()
            tel = str(client.get("telephone", "")).lower()
            ville = str(client.get("ville", "")).lower()

            if search_term and not (search_term in nom or search_term in email or search_term in tel or search_term in ville):
                continue

            visible_clients += 1

            if "documents" not in client or not isinstance(client["documents"], list):
                client["documents"] = []

            details_text = f"✉️ {client.get('email') or 'Non renseigné'}   |   📞 {client.get('telephone') or 'Non renseigné'}\n"
            details_text += f"📍 {client.get('adresse') or '-'}, {client.get('code_postal') or '-'} {client.get('ville') or '-'}"
            if client.get("siret"):
                details_text += f"   |   📑 SIRET: {client['siret']}"

            text_block = ft.Column(
                controls=[
                    ft.Text(client.get("nom", "").upper(), size=13, weight=ft.FontWeight.BOLD, color="#38BDF8"),
                    ft.Text(details_text, size=11, color="#E5E7EB")
                ],
                spacing=4,
                expand=True
            )

            doc_count = len(client["documents"])

            actions_row = ft.Row(
                controls=[
                    ft.IconButton(
                        icon="edit",
                        icon_size=18,
                        icon_color="#38BDF8",
                        tooltip="Modifier",
                        on_click=lambda e, i=idx, c=client: self.charger_client(i, c)
                    ),
                    ft.IconButton(
                        icon="picture_as_pdf",
                        icon_size=18,
                        icon_color="#9CA3AF",
                        tooltip="Fiche PDF",
                        on_click=lambda e, cl=client: self.ouvrir_fiche_pdf(cl)
                    ),
                    ft.IconButton(
                        icon="folder",
                        icon_size=18,
                        icon_color="#4ADE80",
                        tooltip=f"Docs ({doc_count})",
                        on_click=lambda e, i=idx: self.toggle_documents_panel(i)
                    ),
                    ft.IconButton(
                        icon="delete",
                        icon_size=18,
                        icon_color="#F87171",
                        tooltip="Supprimer",
                        on_click=lambda e, i=idx: self.confirm_supprimer_client(i)
                    )
                ],
                alignment=ft.MainAxisAlignment.END,
                spacing=0
            )

            card_content = ft.Column(
                controls=[
                    ft.Row(
                        controls=[text_block, actions_row],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER
                    )
                ],
                spacing=10
            )

            if self.opened_docs_idx == idx:
                card_content.controls.append(self.build_documents_panel(client, idx))

            card = ft.Container(
                content=card_content,
                bgcolor="#242426",
                border=safe_border(1, "#3A3A3C"),
                border_radius=8,
                padding=12
            )

            self.list_column.controls.append(card)

        if visible_clients == 0 and search_term:
            self.list_column.controls.append(
                ft.Container(
                    content=ft.Text("🔍 Aucun client ne correspond à votre recherche.", size=12, italic=True, color="#636366"),
                    alignment=ft.alignment.center,
                    padding=20
                )
            )

        if force_update and self.page:
            self.page.update()

    def toggle_documents_panel(self, client_idx):
        """Déplie ou replie le panneau de gestion des pièces jointes."""
        self.opened_docs_idx = None if self.opened_docs_idx == client_idx else client_idx
        self.refresh_client_list()

    def build_documents_panel(self, client, client_idx):
        """Génère le sous-panneau de gestion des pièces jointes."""
        categories = ["Contrat", "Facture", "Devis", "Attestation", "Fiche Tech.", "Courrier", "Autre"]
        cat_dropdown = ft.Dropdown(
            options=[ft.dropdown.Option(key=c, text=c) for c in categories],
            value="Contrat",
            width=130,
            text_size=12,
            content_padding=8,
            border_radius=6,
            border_color="#48484A"
        )

        btn_add = ft.ElevatedButton(
            content=ft.Text("➕ Joindre PDF"),
            bgcolor=self.accent_color,
            color="white",
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6)),
            height=34,
            on_click=lambda e: self.lancer_import_pdf(client_idx, cat_dropdown.value)
        )

        tools_row = ft.Row(
            controls=[
                ft.Text("Catégorie :", size=11, color="#AEAEB2"),
                cat_dropdown,
                btn_add
            ],
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

        rows_column = ft.Column(spacing=5)

        if not client["documents"]:
            rows_column.controls.append(
                ft.Text("Aucun document rattaché à ce client.", size=11, italic=True, color="#636366")
            )
        else:
            colors = {"Contrat": "#3B82F6", "Facture": "#10B981", "Devis": "#F59E0B", "Attestation": "#8B5CF6"}
            for doc_idx, doc in enumerate(client["documents"]):
                badge_color = colors.get(doc.get('categorie', ''), "#6B7280")

                row = ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Text(doc.get('categorie', '').upper(), size=9, weight=ft.FontWeight.BOLD, color="white"),
                                bgcolor=badge_color,
                                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                                border_radius=4
                            ),
                            ft.Text(doc.get("nom", ""), size=11, color="#E5E7EB", expand=True),
                            ft.Row(
                                controls=[
                                    ft.IconButton(
                                        icon="remove_red_eye",
                                        icon_size=16,
                                        icon_color="#9CA3AF",
                                        tooltip="Ouvrir",
                                        on_click=lambda e, d=doc: self.ouvrir_pdf(d)
                                    ),
                                    ft.IconButton(
                                        icon="delete",
                                        icon_size=16,
                                        icon_color="#F87171",
                                        tooltip="Supprimer",
                                        on_click=lambda e, c_idx=client_idx, d_idx=doc_idx: self.confirm_supprimer_pdf(c_idx, d_idx)
                                    )
                                ],
                                spacing=0
                            )
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    ),
                    bgcolor="#141416",
                    padding=6,
                    border_radius=4
                )
                rows_column.controls.append(row)

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("📁 Pièces jointes & Classement PDF", size=11, weight=ft.FontWeight.BOLD, color="#A7F3D0"),
                    tools_row,
                    rows_column
                ],
                spacing=8
            ),
            bgcolor="#1A1A1C",
            border=safe_border(1, "#48484A"),
            border_radius=6,
            padding=10
        )

    def lancer_import_pdf(self, client_idx, categorie):
        """Ouvre l'explorateur de fichiers local pour inclure un PDF."""
        self.current_upload_client_idx = client_idx
        self.current_upload_categorie = categorie
        self.file_picker.pick_files(allowed_extensions=["pdf"])

    def on_file_picker_result(self, e: ft.FilePickerResultEvent):
        """Copie physiquement le fichier sélectionné vers le dossier de l'application."""
        if not e.files:
            return

        client_idx = getattr(self, "current_upload_client_idx", None)
        categorie = getattr(self, "current_upload_categorie", "Autre")
        if client_idx is None or client_idx >= len(self.app.clients):
            return

        client = self.app.clients[client_idx]
        picked_file = e.files[0]

        try:
            source_path = picked_file.path
            if not source_path:
                return

            base_dir = Path(getattr(self.app, "data_dir", "data")) / "documents_clients"
            nom_propre = "".join(c for c in client.get("nom", "Inconnu") if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
            client_dir = base_dir / nom_propre
            client_dir.mkdir(parents=True, exist_ok=True)

            dest_file = client_dir / picked_file.name

            compteur = 1
            while dest_file.exists():
                dest_file = client_dir / f"{Path(picked_file.name).stem}_{compteur}{Path(picked_file.name).suffix}"
                compteur += 1

            shutil.copy(str(source_path), str(dest_file))

            try:
                chemin_relatif = str(dest_file.relative_to(Path(getattr(self.app, "data_dir", "."))))
            except ValueError:
                chemin_relatif = str(dest_file)

            client["documents"].append({
                "nom": dest_file.name,
                "categorie": categorie,
                "chemin": chemin_relatif
            })

            if hasattr(self.app, "save_data"):
                self.app.save_data()
            self.refresh_client_list()
            self.show_snack("Document rattaché avec succès !")

        except Exception as ex:
            self.show_snack(f"Erreur d'importation : {ex}", is_error=True)

    def ouvrir_pdf(self, doc):
        """Envoie le document vers le visualiseur de documents."""
        try:
            base_dir = Path(getattr(self.app, "data_dir", "."))
            file_path = base_dir / doc["chemin"]
            if file_path.exists():
                self.app.pdf_file_path = str(file_path)
                self.app.navigate_to("PDFViewer", pdf_path=str(file_path))
            else:
                self.show_snack("Le fichier physique est introuvable sur l'appareil.", is_error=True)
        except Exception as ex:
            self.show_snack(f"Impossible d'ouvrir le document : {ex}", is_error=True)

    def ouvrir_fiche_pdf(self, client):
        """Génère une fiche synthétique au format PDF pour le client sélectionné."""
        nom_clean = "".join(c for c in client.get("nom", "INCONNU") if c.isalnum()).upper()
        num_fiche = f"FICHE-CLI-{nom_clean[:12]}"

        donnees_fiche = {
            "type_doc_interne": "fiche_contact",
            "type_contact": "client",
            "numero": num_fiche,
            "nom": client.get("nom", "-"),
            "adresse": client.get("adresse", "-"),
            "code_postal": client.get("code_postal", "-"),
            "ville": client.get("ville", "-"),
            "siret": client.get("siret", "-"),
            "email": client.get("email", "-"),
            "telephone": client.get("telephone", "-"),
            "pdf_path": client.get("pdf_path", "")
        }

        self.app.current_document = donnees_fiche
        self.app.navigate_to("PDFViewer")

    def charger_client(self, idx, client):
        """Passe le formulaire en mode édition."""
        self.editing_idx = idx
        self.lbl_form_title.value = f"✏️ Modifier le client #{idx + 1}"
        self.lbl_form_title.color = "#C2410C"
        
        if hasattr(self.btn_save.content, "value"):
            self.btn_save.content.value = "💾 Appliquer"
        else:
            self.btn_save.content = ft.Text("💾 Appliquer")
            
        self.btn_save.bgcolor = "#C2410C"

        for key in self.fields:
            self.fields[key].value = str(client.get(key, ""))
        if self.page:
            self.page.update()

    def vider_champs(self):
        """Réinitialise les champs de saisie."""
        self.editing_idx = None
        self.lbl_form_title.value = "📝 Ajouter un nouveau client"
        self.lbl_form_title.color = self.accent_color

        if hasattr(self.btn_save.content, "value"):
            self.btn_save.content.value = "💾 Enregistrer"
        else:
            self.btn_save.content = ft.Text("💾 Enregistrer")

        self.btn_save.bgcolor = "#15803D"

        for key in self.fields:
            self.fields[key].value = ""
        self.refresh_client_list()

    def valider_client(self):
        """Valide et enregistre la fiche client."""
        nom = self.fields["nom"].value.strip() if self.fields["nom"].value else ""

        if not nom:
            self.show_snack("Le Nom / Raison Sociale est obligatoire.", is_error=True)
            return

        if self.editing_idx is not None:
            for key in self.fields:
                self.app.clients[self.editing_idx][key] = self.fields[key].value.strip() if self.fields[key].value else ""
            self.show_snack("Client modifié avec succès !")
        else:
            client_data = {key: (self.fields[key].value.strip() if self.fields[key].value else "") for key in self.fields}
            client_data["documents"] = []
            self.app.clients.append(client_data)
            self.show_snack("Client ajouté avec succès !")

        if hasattr(self.app, "save_data"):
            self.app.save_data()
        self.vider_champs()

    def confirm_supprimer_client(self, idx):
        """Affiche une confirmation avant de supprimer un client."""
        def on_confirm():
            client = self.app.clients[idx]
            if "documents" in client:
                for doc in client["documents"]:
                    try:
                        file_path = Path(getattr(self.app, "data_dir", ".")) / doc["chemin"]
                        if file_path.exists():
                            os.remove(file_path)
                    except Exception:
                        pass
            self.app.clients.pop(idx)
            if hasattr(self.app, "save_data"):
                self.app.save_data()
            self.opened_docs_idx = None
            self.refresh_client_list()
            self.vider_champs()
            self.show_snack("Client supprimé.")

        self.show_confirm_dialog(
            "Confirmation de suppression",
            "Voulez-vous vraiment supprimer ce client et toutes ses pièces jointes ?",
            on_confirm
        )

    def confirm_supprimer_pdf(self, client_idx, doc_idx):
        """Affiche une confirmation avant de détacher un PDF."""
        def on_confirm():
            client = self.app.clients[client_idx]
            doc = client["documents"][doc_idx]
            try:
                base_dir = Path(getattr(self.app, "data_dir", "."))
                file_path = base_dir / doc["chemin"]
                if file_path.exists():
                    os.remove(file_path)
                client["documents"].pop(doc_idx)
                if hasattr(self.app, "save_data"):
                    self.app.save_data()
                self.refresh_client_list()
                self.show_snack("Document supprimé.")
            except Exception as ex:
                self.show_snack(f"Erreur de suppression : {ex}", is_error=True)

        client = self.app.clients[client_idx]
        doc = client["documents"][doc_idx]
        self.show_confirm_dialog(
            "Détacher le document",
            f"Voulez-vous vraiment supprimer le document '{doc['nom']}' ?",
            on_confirm
        )

    def show_confirm_dialog(self, title, message, on_confirm):
        """Affiche une boîte de dialogue modale de confirmation."""
        def close_dialog(e):
            self._fermer_dialogue(dialog)

        def confirm_action(e):
            self._fermer_dialogue(dialog)
            on_confirm()

        dialog = ft.AlertDialog(
            title=ft.Text(title),
            content=ft.Text(message),
            actions=[
                ft.TextButton(content=ft.Text("Annuler"), on_click=close_dialog),
                ft.TextButton(content=ft.Text("Confirmer"), on_click=confirm_action, style=ft.ButtonStyle(color="#EF4444")),
            ],
        )
        self._ouvrir_dialogue(dialog)

    def _ouvrir_dialogue(self, dlg):
        page_obj = self.page or getattr(self.app, "page", None)
        if page_obj:
            try:
                page_obj.open(dlg)
            except Exception:
                page_obj.overlay.append(dlg)
                dlg.open = True
                page_obj.update()

    def _fermer_dialogue(self, dlg):
        page_obj = self.page or getattr(self.app, "page", None)
        if page_obj:
            try:
                page_obj.close(dlg)
            except Exception:
                dlg.open = False
                page_obj.update()

    def show_snack(self, message, is_error=False):
        """Affiche un toast informatif au bas de l'écran."""
        color = "#B91C1C" if is_error else "#15803D"
        page_obj = self.page or getattr(self.app, "page", None)
        if page_obj:
            snack = ft.SnackBar(content=ft.Text(message), bgcolor=color)
            try:
                page_obj.open(snack)
            except Exception:
                page_obj.snack_bar = snack
                snack.open = True
                page_obj.update()
