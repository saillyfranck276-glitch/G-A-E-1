import json
import shutil
import zipfile
from pathlib import Path
import flet as ft

class ReglagesView(ft.Container):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.expand = True
        self.padding = 15
        
        # Récupération de la couleur d'accentuation actuelle
        self.accent_color = self.app.entreprise.get("accent_color", "#2B719E") if hasattr(self.app, "entreprise") else "#2B719E"

        # Initialisation des sélecteurs de fichiers (Obligatoire pour les backups sous Android)
        self.export_picker = ft.FilePicker(on_result=self._on_export_result)
        self.import_picker = ft.FilePicker(on_result=self._on_import_result)

        # --- CONTENU DES CARTES DE CONFIGURATION ---

        # 1. Thème Apparence
        theme_btn = ft.SegmentedButton(
            segments=[
                ft.Segment(value="Dark", label=ft.Text("Sombre")),
                ft.Segment(value="Light", label=ft.Text("Clair"))
            ],
            selected={self.app.entreprise.get("theme_pref", "Dark")},
            on_change=self._changer_theme
        )
        
        # 2. Couleur de l'application
        self.mapping_couleurs = {"Bleu": "#2B719E", "Vert": "#2E7D32", "Orange": "#D97706", "Violet": "#6D28D9", "Rouge": "#C62828"}
        color_btn = ft.SegmentedButton(
            segments=[ft.Segment(value=k, label=ft.Text(k)) for k in self.mapping_couleurs.keys()],
            selected={self.app.entreprise.get("accent_color_name", "Bleu")},
            on_change=self._changer_couleur_theme
        )
        
        # 3. Sauvegarde Locale
        backup_row = ft.Row(
            controls=[
                ft.ElevatedButton("Créer un Backup Global", bgcolor=ft.colors.GREEN_700, color=ft.colors.WHITE, on_click=self._faire_sauvegarde, expand=True),
                ft.ElevatedButton("Restaurer", bgcolor=ft.colors.RED_700, color=ft.colors.WHITE, on_click=self._restaurer_sauvegarde, expand=True),
            ],
            spacing=10
        )

        # 4. Sauvegarde Cloud
        cloud_column = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.ElevatedButton("Exporter vers Cloud", bgcolor=ft.colors.BLUE_700, color=ft.colors.WHITE, on_click=lambda e: self.show_snack("Poussée Cloud à implémenter selon votre API."), expand=True),
                        ft.ElevatedButton("Importer du Cloud", bgcolor=ft.colors.BLUE_900, color=ft.colors.WHITE, on_click=lambda e: self.show_snack("Récupération Cloud à implémenter selon votre API."), expand=True),
                    ],
                    spacing=10
                ),
                ft.ElevatedButton("🔧 Configurer les accès Cloud", on_click=self._popup_cloud, width=600, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)))
            ],
            spacing=5
        )

        # 5. Numérotation Séquentielle
        num_btn = ft.ElevatedButton("Modifier les Séquences", on_click=self._popup_numerotation, width=600)

        # 6. Messagerie SMTP / IMAP
        email_btn = ft.ElevatedButton("Configurer la Messagerie", on_click=self._popup_email, width=600)

        # 7. Facturation Dématérialisée (Factur-X)
        etat_initial = self.app.entreprise.get("demat_active", False)
        demat_switch = ft.Switch(label="Activer le format Factur-X", value=etat_initial, on_change=lambda e: self._toggle_demat(e.control.value))
        demat_column = ft.Column(
            controls=[
                demat_switch,
                ft.ElevatedButton("Options avancées Chorus Pro", on_click=self._popup_demat, width=600)
            ],
            spacing=5
        )

        # 8. Seuils de CA
        seuils_btn = ft.ElevatedButton("Gérer mes alertes de CA", on_click=self._popup_seuils, width=600)

        # --- ASSEMBLAGE DE LA PAGE PRINCIPALE ---
        self.content = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.IconButton(ft.icons.ARROW_BACK_ROUNDED, on_click=lambda e: self.app.navigate_to("Dashboard")),
                        ft.Text("⚙️ Paramètres & Configuration", size=24, weight=ft.FontWeight.BOLD),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),
                ft.Container(
                    content=ft.ResponsiveRow(
                        controls=[
                            self._creer_base_card("🎨 Apparence & Mode", "Basculez entre le mode sombre et le mode clair.", theme_btn),
                            self._creer_base_card("✨ Couleur de l'application", "Choisissez la couleur d'accentuation des boutons du logiciel.", color_btn),
                            self._creer_base_card("💾 Sauvegarde Locale", "Sécurisez vos factures, devis, fiches clients et agenda en local.", backup_row),
                            self._creer_base_card("☁️ Sauvegarde Cloud", "Synchronisez et récupérez vos bases de données depuis un serveur distant.", cloud_column),
                            self._creer_base_card("🔢 Structure des Numéros", "Définissez le format séquentiel de vos factures et devis.", num_btn),
                            self._creer_base_card("📧 Configuration Messagerie", "Paramétrez l'envoi (SMTP) et la réception (IMAP) de vos e-mails.", email_btn),
                            self._creer_base_card("🧾 Facturation Dématérialisée", "Préparez la transition légale obligatoire vers Chorus Pro.", demat_column),
                            self._creer_base_card("⚠️ Seuils & Plafonds de CA", "Suivez vos limites de Chiffre d'Affaires d'auto-entrepreneur.", seuils_btn),
                        ],
                        spacing=15
                    ),
                    expand=True,
                )
            ],
            spacing=20,
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )

    def did_mount(self):
        """Attachement des composants FilePickers globaux à l'overlay de la page lors de l'affichage"""
        if self.export_picker not in self.app.page.overlay:
            self.app.page.overlay.append(self.export_picker)
        if self.import_picker not in self.app.page.overlay:
            self.app.page.overlay.append(self.import_picker)
        self.app.page.update()

    def _creer_base_card(self, titre, description, content_control):
        """Génère un conteneur de carte stylisé et responsive"""
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(titre, size=15, weight=ft.FontWeight.BOLD),
                    ft.Text(description, size=12, color=ft.colors.GREY_400),
                    ft.Container(content=content_control, padding=ft.padding.only(top=5))
                ],
                spacing=5,
                tight=True
            ),
            bgcolor="#1E1E20",
            border_radius=12,
            border=ft.border.all(1, "#2A2A2E"),
            padding=15,
            col={"xs": 12, "sm": 6}
        )

    def _get_active_data_dir(self):
        if hasattr(self.app, "data_dir"):
            return Path(self.app.data_dir)
        return Path(".").resolve() / "data"

    # --- ACTIONS THÈMES ---
    def _changer_theme(self, e):
        choix = next(iter(e.control.selected), "Dark")
        self.app.page.theme_mode = ft.ThemeMode.DARK if choix == "Dark" else ft.ThemeMode.LIGHT
        self.app.entreprise["theme_pref"] = choix
        self.app.save_data()
        self.app.page.update()

    def _changer_couleur_theme(self, e):
        nom_couleur = list(e.control.selected)[0]
        hex_color = self.mapping_couleurs.get(nom_couleur, "#2B719E")
        self.app.entreprise.update({"accent_color_name": nom_couleur, "accent_color": hex_color})
        self.app.save_data()
        self.show_snack(f"Teinte globale {nom_couleur} enregistrée. Redémarrez pour appliquer partout.")

    def _toggle_demat(self, valeur):
        self.app.entreprise["demat_active"] = bool(valeur)
        self.app.save_data()

    # --- SAUVEGARDES ---
    def _faire_sauvegarde(self, e):
        self.export_picker.save_file(file_name="backup_global.zip", allowed_extensions=["zip"])

    def _on_export_result(self, e: ft.FilePickerResultEvent):
        if e.path:
            try:
                data_dir = self._get_active_data_dir()
                with zipfile.ZipFile(e.path, 'w', zipfile.ZIP_DEFLATED) as z:
                    for f in ["database.json", "application.db"]:
                        if (data_dir / f).exists():
                            z.write(data_dir / f, arcname=f)
                self.show_snack("Sauvegarde globale exportée avec succès ! ✔")
            except Exception as ex:
                self.show_snack(f"Erreur d'écriture du backup : {ex}", is_error=True)

    def _restaurer_sauvegarde(self, e):
        def confirmation_action(action_confirmee):
            dialog.open = False
            self.app.page.update()
            if action_confirmee:
                self.import_picker.pick_files(allowed_extensions=["zip"])

        dialog = ft.AlertDialog(
            title=ft.Text("🚨 Attention"),
            content=ft.Text("Êtes-vous sûr de vouloir écraser les données actuelles ? Cette action est irréversible."),
            actions=[
                ft.TextButton("Annuler", on_click=lambda _: confirmation_action(False)),
                ft.TextButton("Confirmer l'écrasement", on_click=lambda _: confirmation_action(True), style=ft.ButtonStyle(color=ft.colors.RED_600)),
            ]
        )
        self.app.page.overlay.append(dialog)
        dialog.open = True
        self.app.page.update()

    def _on_import_result(self, e: ft.FilePickerResultEvent):
        if e.files and e.files[0].path:
            try:
                data_dir = self._get_active_data_dir()
                data_dir.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(e.files[0].path, 'r') as z:
                    z.extractall(data_dir)
                self.app.load_data()
                self.show_snack("Données locales restaurées et synchronisées ! ✔")
            except Exception as ex:
                self.show_snack(f"Échec du déploiement de l'archive : {ex}", is_error=True)

    # --- ABSTRACTION MODALE CORRIGÉE ---
    def _ouvrir_popup_formulaire(self, titre, liste_champs, callback_sauvegarde):
        """Crée une fenêtre de saisie modale propre, corrigée pour Flet et adaptée aux mobiles"""
        def fermer(e):
            dialog.open = False
            self.app.page.update()

        def valider(e):
            if callback_sauvegarde():
                fermer(e)

        dialog = ft.AlertDialog(
            title=ft.Text(titre, size=18, weight=ft.FontWeight.BOLD),
            # Limitation propre de la taille via la colonne ou la modale directement
            content=ft.Container(
                content=ft.Column(
                    controls=liste_champs, 
                    spacing=12, 
                    tight=True, 
                    scroll=ft.ScrollMode.AUTO
                ),
                width=420,
                # Correction : La hauteur est fixée directement sur le ft.Container parent du contenu
                height=420 
            ),
            actions=[
                ft.TextButton("Annuler", on_click=fermer),
                ft.TextButton("Enregistrer", on_click=valider, style=ft.ButtonStyle(color=ft.colors.BLUE_ACCENT)),
            ],
        )
        self.app.page.overlay.append(dialog)
        dialog.open = True
        self.app.page.update()

    # --- CONFIGURATIONS FORMULAIRES ---
    def _popup_email(self, e):
        ent = self.app.entreprise
        tf_host = ft.TextField(label="Serveur d'envoi SMTP", value=ent.get("smtp_host", "smtp.gmail.com"))
        tf_port = ft.TextField(label="Port SMTP (ex: 465)", value=ent.get("smtp_port", "465"))
        tf_imap = ft.TextField(label="Serveur de réception IMAP", value=ent.get("imap_host", "imap.gmail.com"))
        tf_imap_port = ft.TextField(label="Port IMAP (ex: 993)", value=ent.get("imap_port", "993"))
        tf_user = ft.TextField(label="Adresse e-mail / Identifiant", value=ent.get("smtp_user", "saillyfranch276@gmail.com"))
        tf_pass = ft.TextField(label="Mot de passe d'application", value=ent.get("smtp_password", ""), password=True, can_reveal_password=True)

        def sauvé():
            ent.update({
                "smtp_host": tf_host.value.strip(), "smtp_port": tf_port.value.strip(),
                "imap_host": tf_imap.value.strip(), "imap_port": tf_imap_port.value.strip(),
                "smtp_user": tf_user.value.strip(), "smtp_password": tf_pass.value.strip()
            })
            self.app.save_data()
            self.show_snack("Configuration Email mise à jour ! ✔")
            return True

        self._ouvrir_popup_formulaire("Messagerie (SMTP & IMAP)", [tf_host, tf_port, tf_imap, tf_imap_port, tf_user, tf_pass], sauvé)

    def _popup_cloud(self, e):
        ent = self.app.entreprise
        dd_prov = ft.Dropdown(
            label="Fournisseur Cloud",
            options=[ft.dropdown.Option(p) for p in ["Google Drive", "Dropbox", "OneDrive", "Serveur FTP/SFTP", "WebDAV"]],
            value=ent.get("cloud_provider", "Google Drive")
        )
        tf_id = ft.TextField(label="Client ID / Identifiant", value=ent.get("cloud_id", ""))
        tf_secret = ft.TextField(label="Client Secret / Mot de passe", value=ent.get("cloud_secret", ""), password=True, can_reveal_password=True)
        tf_url = ft.TextField(label="URL / Chemin distant", value=ent.get("cloud_url", ""))

        def sauvé():
            ent.update({"cloud_provider": dd_prov.value, "cloud_id": tf_id.value.strip(), "cloud_secret": tf_secret.value.strip(), "cloud_url": tf_url.value.strip()})
            self.app.save_data()
            self.show_snack("Configuration Accès Cloud sauvegardée ! ✔")
            return True

        self._ouvrir_popup_formulaire("Configuration Paramètres Cloud", [dd_prov, tf_id, tf_secret, tf_url], sauvé)

    def _popup_numerotation(self, e):
        ent = self.app.entreprise
        tf_f = ft.TextField(label="Préfixe des Factures", value=ent.get("prefix_facture", "F2026-"))
        tf_d = ft.TextField(label="Préfixe des Devis", value=ent.get("prefix_devis", "D2026-"))

        def sauvé():
            ent.update({"prefix_facture": tf_f.value.strip(), "prefix_devis": tf_d.value.strip()})
            self.app.save_data()
            self.show_snack("Préfixes séquentiels modifiés ! ✔")
            return True

        self._ouvrir_popup_formulaire("Séquences de numérotation", [tf_f, tf_d], sauvé)

    def _popup_demat(self, e):
        ent = self.app.entreprise
        tf_c = ft.TextField(label="Numéro d'identifiant Chorus Pro (Siret / Tech)", value=ent.get("chorus_id", ""))

        def sauvé():
            ent["chorus_id"] = tf_c.value.strip()
            self.app.save_data()
            self.show_snack("Identifiant Chorus Pro enregistré ! ✔")
            return True

        self._ouvrir_popup_formulaire("Identifiants Chorus Pro", [tf_c], sauvé)

    def _popup_seuils(self, e):
        ent = self.app.entreprise
        tf_s = ft.TextField(label="Plafond ou Seuil d'alerte (€)", value=str(ent.get("seuil_alerte_ca", 70000)))

        def sauvé():
            try:
                raw_val = tf_s.value.replace(" ", "").replace(",", ".").strip()
                ent["seuil_alerte_ca"] = float(raw_val)
                self.app.save_data()
                self.show_snack("Seuil de sécurité CA mis à jour ! ✔")
                return True
            except ValueError:
                self.show_snack("Veuillez entrer une valeur numérique valide.", is_error=True)
                return False

        self._ouvrir_popup_formulaire("Seuils de Chiffre d'Affaires", [tf_s], sauvé)

    def show_snack(self, message, is_error=False):
        self.app.page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.colors.RED_700 if is_error else ft.colors.GREEN_700
        )
        self.app.page.snack_bar.open = True
        self.app.page.update()