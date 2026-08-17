import flet as ft
from pathlib import Path
import base64
from PIL import Image

CARD_COLOR = "#1E1E22"
PRIMARY_COLOR = "#2B719E"

class EntrepriseView(ft.Container):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.expand = True
        self.padding = 20

        # 🛡️ CORRECTION ALIGNEMENT COMPILATION
        if hasattr(app, "data_dir"):
            self.data_folder = app.data_dir
        else:
            self.data_folder = getattr(app, "base_dir", Path(__file__).resolve().parent.parent) / "data"
            
        self.logo_path = self.data_folder / "logo.png"
        self.entreprise = getattr(app, "entreprise", {})
        
        # Initialisation des valeurs par défaut
        self.init_default_values()

        # Initialisation du FilePicker pour le Logo
        self.file_picker = ft.FilePicker(on_result=self._import_company_logo)
        if self.file_picker not in self.app.page.overlay:
            self.app.page.overlay.append(self.file_picker)

        self._build_interface()
        self._update_logo_preview()

    def init_default_values(self):
        """S'assure que les variables de configuration importantes existent en mémoire"""
        defaults = {
            "nom": "VOTRE ENTREPRISE", "statut_juridique": "Micro-entreprise", "siret": "",
            "adresse": "", "telephone": "", "email": "",
            "iban": "", "bic": "", "taux_charges": "21.1",
            "soumis_tva": "Non",
            "mention_tva": "TVA non applicable, art. 293 B du CGI",
            "rc_pro": "Assurance RC Pro & Décennale : [Nom Compagnie] - Contrat n° [0000] - Zone : [France]",
            "conditions_reglement": "Paiement à réception. Pénalités de retard : 3 fois le taux d’intérêt légal. Indemnité forfaitaire de 40€ pour frais de recouvrement."
        }
        for key, default_val in defaults.items():
            if key not in self.entreprise or not self.entreprise[key]:
                self.entreprise[key] = default_val

    def _build_interface(self):
        # --- 1. ÉLÉMENTS DE LA SECTION LOGO ---
        self.img_logo = ft.Image(width=120, height=60, fit=ft.ImageFit.CONTAIN, visible=False)
        self.lbl_no_logo = ft.Text("Aucun logo configuré", color=ft.colors.GREY_400)
        
        logo_card = ft.Container(
            content=ft.Column([
                ft.Text("Logo officiel pour les PDF :", size=13, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.Row([self.img_logo, self.lbl_no_logo], alignment=ft.MainAxisAlignment.START),
                    ft.ElevatedButton(
                        "🖼️ Importer un Logo",
                        bgcolor=PRIMARY_COLOR,
                        color=ft.colors.WHITE,
                        on_click=lambda _: self.file_picker.pick_files(
                            file_type=ft.FilePickerFileType.CUSTOM,
                            allowed_extensions=["png", "jpg", "jpeg"]
                        )
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ], spacing=10),
            bgcolor=CARD_COLOR,
            border=ft.border.all(1, "#2A2A2E"),
            border_radius=8,
            padding=15
        )

        # --- 2. SECTION CONFIGURATION ET OPTIONS ---
        statut_options = ["Micro-entreprise", "EI (Entreprise Individuelle)", "EURL", "SARL", "SASU", "SAS"]
        current_statut = self.entreprise.get("statut_juridique", "Micro-entreprise")
        if current_statut not in statut_options:
            statut_options.append(current_statut)

        self.dd_statut = ft.Dropdown(
            label="Type d'entreprise",
            options=[ft.dropdown.Option(opt) for opt in statut_options],
            value=current_statut,
            width=300
        )

        self.rg_tva = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="Non", label="Non (Franchise en base)"),
                ft.Radio(value="Oui", label="Oui (Assujetti à la TVA)")
            ], spacing=20),
            value=self.entreprise.get("soumis_tva", "Non"),
            on_change=self._on_tva_change
        )

        options_card = ft.Container(
            content=ft.Column([
                self.dd_statut,
                ft.Row([
                    ft.Text("Soumis à la TVA :", weight=ft.FontWeight.BOLD, size=13),
                    self.rg_tva
                ], alignment=ft.MainAxisAlignment.START, spacing=20)
            ], spacing=15),
            bgcolor="transparent"
        )

        # --- 3. SECTION MENTIONS LÉGALES OBLIGATOIRES ---
        # 💡 Corrigé : Retrait des expand=True qui faisaient crasher la hauteur sous scroll
        self.tf_legal_tva = ft.TextField(label="Mention d'application / Exonération de TVA", value=str(self.entreprise.get("mention_tva", "")))
        self.tf_rc_pro = ft.TextField(label="Assurance Décennale / RC Professionnelle", value=str(self.entreprise.get("rc_pro", "")))
        self.tf_conditions = ft.TextField(label="Conditions de règlement & Pénalités de retard par défaut", value=str(self.entreprise.get("conditions_reglement", "")))

        legal_card = ft.Container(
            content=ft.Column([
                ft.Text("📜 Mentions Légales Obligatoires (Pied de page PDF)", size=14, weight=ft.FontWeight.BOLD, color=PRIMARY_COLOR),
                ft.Divider(height=1, color="#2A2A2E"),
                self.tf_legal_tva,
                self.tf_rc_pro,
                self.tf_conditions
            ], spacing=15, horizontal_alignment=ft.CrossAxisAlignment.STRETCH), # 💡 Stretch pour occuper toute la largeur
            bgcolor=CARD_COLOR,
            border=ft.border.all(1, "#2A2A2E"),
            border_radius=8,
            padding=20
        )

        # --- 4. SECTION COORDONNÉES CLASSIQUES ---
        form_fields = [
            ("nom", "Nom de l'entreprise / Nom Commercial :"),
            ("siret", "Numéro SIRET (14 chiffres) :"),
            ("adresse", "Adresse postale complète (Siège social) :"),
            ("telephone", "Numéro de téléphone :"),
            ("email", "Adresse e-mail de contact :"),
            ("iban", "Code IBAN (Pour les règlements) :"),
            ("bic", "Code BIC / SWIFT :"),
            ("taux_charges", "Taux de charges URSSAF % (ex: 21.1) :")
        ]

        self.entries = {}
        coordonnees_controls = [
            ft.Text("📍 Coordonnées & Identification", size=14, weight=ft.FontWeight.BOLD, color=PRIMARY_COLOR),
            ft.Divider(height=1, color="#2A2A2E")
        ]

        for key, label_text in form_fields:
            is_multiline = (key == "adresse")
            # 💡 Corrigé : Retrait de expand=True ici aussi
            tf = ft.TextField(
                label=label_text, 
                value=str(self.entreprise.get(key, "")), 
                multiline=is_multiline,
                min_lines=2 if is_multiline else 1
            )
            coordonnees_controls.append(tf)
            self.entries[key] = tf

        coordonnees_card = ft.Container(
            content=ft.Column(coordonnees_controls, spacing=15, horizontal_alignment=ft.CrossAxisAlignment.STRETCH), # 💡 Stretch pour occuper toute la largeur
            bgcolor=CARD_COLOR,
            border=ft.border.all(1, "#2A2A2E"),
            border_radius=8,
            padding=20
        )

        # --- CONTENU GLOBAL DÉFILANT ---
        self.content = ft.Column(
            controls=[
                # En-tête avec bouton de sauvegarde
                ft.Row([
                    ft.Text("🏢 Réglages Entreprise & Logo", size=26, weight=ft.FontWeight.BOLD),
                    ft.ElevatedButton(
                        "💾 Enregistrer les modifications",
                        bgcolor=PRIMARY_COLOR,
                        color=ft.colors.WHITE,
                        icon=ft.icons.SAVE,
                        on_click=self._save_company,
                        height=45
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                
                ft.Container(height=10),
                logo_card,
                options_card,
                legal_card,
                coordonnees_card,
                ft.Container(height=20)
            ],
            spacing=20,
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )

    def _on_tva_change(self, e):
        """Met à jour dynamiquement le champ de mention légale selon le choix TVA"""
        if self.rg_tva.value == "Oui":
            self.tf_legal_tva.value = "Assujetti à la TVA - Numéro d'identification : [Votre N° TVA]"
        else:
            self.tf_legal_tva.value = "TVA non applicable, art. 293 B du CGI"
        self.tf_legal_tva.update()

    def _import_company_logo(self, e: ft.FilePickerResultEvent):
        """Gère l'importation de l'image sélectionnée par le FilePicker"""
        if e.files:
            file_path = e.files[0].path
            if file_path:
                try:
                    self.logo_path.parent.mkdir(parents=True, exist_ok=True)
                    img = Image.open(file_path)
                    img.save(self.logo_path, "PNG")
                    self._update_logo_preview()
                    self.show_snack("Le logo de l'entreprise a été mis à jour avec succès ! ✅")
                except Exception as ex:
                    self.show_snack(f"Erreur d'import : {ex}", is_error=True)

    def _update_logo_preview(self):
        """Recharge l'aperçu du logo de manière sûre à l'aide d'un encodage Base64 (évite le cache Flet)"""
        if self.logo_path.exists():
            try:
                with open(self.logo_path, "rb") as img_file:
                    encoded_string = base64.b64encode(img_file.read()).decode("utf-8")
                
                self.img_logo.src_base64 = encoded_string
                self.img_logo.visible = True
                self.lbl_no_logo.visible = False
            except Exception as e:
                self.lbl_no_logo.value = "Erreur de lecture du logo"
                self.lbl_no_logo.visible = True
                self.img_logo.visible = False
                print(f"[WARN] _update_logo_preview: {e}")
        else:
            self.lbl_no_logo.value = "Aucun logo configuré"
            self.lbl_no_logo.visible = True
            self.img_logo.visible = False
        
        if self.img_logo.page:
            self.img_logo.update()
        if self.lbl_no_logo.page:
            self.lbl_no_logo.update()

    def _save_company(self, e):
        """Valide, nettoie et sauvegarde les données de l'entreprise"""
        taux_brut = self.entries["taux_charges"].value.strip()
        taux_propre = taux_brut.replace("%", "").replace(" ", "").replace(",", ".").strip()
        
        if taux_propre:
            try:
                float(taux_propre)
            except ValueError:
                self.show_snack("Le taux de charges URSSAF doit être un nombre valide (ex: 21.1 ou 21,1).", is_error=True)
                return
        else:
            taux_propre = "0.0"

        self.entreprise["statut_juridique"] = self.dd_statut.value
        self.entreprise["soumis_tva"] = self.rg_tva.value
        self.entreprise["tva_activee"] = (self.rg_tva.value == "Oui")
        
        self.entreprise["mention_tva"] = self.tf_legal_tva.value.strip()
        self.entreprise["rc_pro"] = self.tf_rc_pro.value.strip()
        self.entreprise["conditions_reglement"] = self.tf_conditions.value.strip()

        for key in self.entries: 
            if key == "taux_charges":
                self.entreprise[key] = taux_propre
            else:
                self.entreprise[key] = self.entries[key].value.strip()
            
        if hasattr(self.app, "save_data"):
            self.app.save_data()
            
        if hasattr(self.app, "creer_menu_sidebar"):
            self.app.creer_menu_sidebar()
            
        self.show_snack("Les informations et mentions légales ont été enregistrées avec succès. ✅")

    def show_snack(self, message, is_error=False):
        """Affiche une notification Snack-bar moderne en bas de l'application"""
        self.app.page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.colors.RED_700 if is_error else ft.colors.GREEN_700
        )
        self.app.page.snack_bar.open = True
        self.app.page.update()