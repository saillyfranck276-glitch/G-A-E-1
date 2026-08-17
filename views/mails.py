import flet as ft
from datetime import datetime

CARD_COLOR = "#1E1E22"
PRIMARY_COLOR = "#2B719E"
BG_COLOR = "#1A1A1C"
HOVER_COLOR = "#2A2A2E"
SELECTED_COLOR = "#242830"

class MailsView(ft.Container):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.expand = True
        self.padding = 15
        self.current_folder = "📥 Reçus"
        self.selected_mail = None  # Garde en mémoire le mail actif
        
        # Récupération de la couleur d'accentuation globale
        self.accent_color = getattr(app, "entreprise", {}).get("accent_color", PRIMARY_COLOR) if hasattr(app, "entreprise") else PRIMARY_COLOR
        
        # Configuration des dossiers
        self.folders = ["📥 Reçus", "📤 Envoyés", "🗑️ Corbeille"]
        
        self._build_interface()

    def did_mount(self):
        """Appelé quand le contrôle est monté : charge la liste initiale."""
        self.refresh_mail_list()

    def _build_interface(self):
        # --- SIDEBAR (Dossiers + Bouton Rédiger) ---
        self.btn_compose = ft.ElevatedButton(
            text="📝 Rédiger",
            bgcolor=self.accent_color,
            color=ft.colors.WHITE,
            height=45,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
            on_click=lambda e: self.ouvrir_redaction()
        )

        self.sidebar_folders = ft.Column(spacing=5)
        self._render_sidebar_buttons()

        self.sidebar = ft.Column(
            controls=[
                ft.Text("Messagerie", weight=ft.FontWeight.BOLD, size=18, color=ft.colors.WHITE),
                ft.Container(height=10),
                self.btn_compose,
                ft.Container(height=10),
                ft.Divider(color="#2A2A2E"),
                self.sidebar_folders
            ],
            width=160,
            spacing=10
        )

        # --- LISTE DES MAILS ---
        self.mail_list_container = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=8)
        
        # --- ZONE DE LECTURE / RÉDACTION ---
        self.reader_content = ft.Column(expand=True)
        self.reader_container = ft.Container(
            content=self.reader_content,
            bgcolor=CARD_COLOR,
            padding=25,
            border_radius=12,
            expand=True,
            border=ft.border.all(1, "#2A2A2E")
        )

        # Afficher l'état vide initial dans la zone de lecture
        self._afficher_placeholder_lecture("Sélectionnez un message pour le lire")

        # --- MISE EN PAGE PRINCIPALE ---
        self.content = ft.Row([
            ft.Container(content=self.sidebar, padding=5),
            ft.VerticalDivider(color="#2A2A2E", width=1),
            ft.Container(content=self.mail_list_container, width=320, padding=5),
            ft.VerticalDivider(color="#2A2A2E", width=1),
            self.reader_container
        ], expand=True)

    def _render_sidebar_buttons(self):
        """Regénère les boutons de la sidebar pour appliquer le style 'actif'."""
        self.sidebar_folders.controls.clear()
        for f in self.folders:
            is_active = f == self.current_folder
            self.sidebar_folders.controls.append(
                ft.TextButton(
                    text=f,
                    style=ft.ButtonStyle(
                        color=ft.colors.WHITE if is_active else ft.colors.GREY_400,
                        bgcolor="#2A2A2E" if is_active else ft.colors.TRANSPARENT,
                        shape=ft.RoundedRectangleBorder(radius=6),
                        padding=12
                    ),
                    on_click=lambda e, folder=f: self.switch_folder(folder),
                    width=160
                )
            )

    def switch_folder(self, folder_name):
        self.current_folder = folder_name
        self.selected_mail = None
        self._render_sidebar_buttons()
        self.refresh_mail_list()
        self._afficher_placeholder_lecture(f"Aucun message sélectionné dans {folder_name.split()[-1]}")
        self.update()

    def refresh_mail_list(self):
        """Affiche la liste des mails filtrés et stylisés."""
        self.mail_list_container.controls.clear()
        
        mails = getattr(self.app, "mails", [])
        if not mails:
            # Injecte des faux mails de démo si la liste est totalement vide au premier lancement
            mails = [
                {"sujet": "Bienvenue sur votre CRM", "expediteur": "support@crm.com", "destinataire": "vous@entreprise.com", "contenu": "Bonjour,\n\nBienvenue dans votre nouvel outil de gestion intégré ! Tout est opérationnel.", "dossier": "inbox", "date": "Aujourd'hui, 10:14", "lu": False},
                {"sujet": "Devis validé - Client Dupont", "expediteur": "dupont@gmail.com", "destinataire": "vous@entreprise.com", "contenu": "Merci pour votre réactivité, j'ai signé le devis en ligne.", "dossier": "inbox", "date": "Hier, 17:30", "lu": True}
            ]
            self.app.mails = mails

        count = 0
        for mail in mails:
            # Logique de filtrage par dossier
            if self.current_folder == "📥 Reçus" and mail.get("dossier") != "inbox": continue
            if self.current_folder == "📤 Envoyés" and mail.get("dossier") != "sent": continue
            if self.current_folder == "🗑️ Corbeille" and mail.get("dossier") != "trash": continue

            count += 1
            is_selected = (self.selected_mail == mail)
            is_unread = not mail.get("lu", True) and mail.get("dossier") == "inbox"

            # En fonction du dossier, on adapte l'affichage (Expéditeur ou Destinataire)
            tiers_label = f"À : {mail.get('destinataire', 'Inconnu')}" if mail.get("dossier") == "sent" else mail.get("expediteur", "Inconnu")

            card = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(
                            mail.get("sujet", "(Sans sujet)"), 
                            weight=ft.FontWeight.BOLD if is_unread else ft.FontWeight.NORMAL, 
                            size=13,
                            color=ft.colors.WHITE if (is_unread or is_selected) else ft.colors.GREY_300,
                            expand=True,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS
                        ),
                        # Petite pastille bleue si le mail n'est pas lu
                        ft.Container(width=8, height=8, bgcolor=self.accent_color, border_radius=4, visible=is_unread)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Container(height=2),
                    ft.Row([
                        ft.Text(tiers_label, size=11, color=ft.colors.GREY_400 if not is_selected else ft.colors.WHITE, expand=True, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(mail.get("date", ""), size=10, color=ft.colors.GREY_500)
                    ])
                ], spacing=2),
                padding=12,
                border_radius=8,
                bgcolor=SELECTED_COLOR if is_selected else "#242426",
                border=ft.border.all(1, self.accent_color if is_selected else ft.colors.TRANSPARENT),
                on_click=lambda e, m=mail: self.ouvrir_lecture(m),
                on_hover=lambda e: self._on_card_hover(e),
                margin=ft.margin.only(right=5)
            )
            self.mail_list_container.controls.append(card)

        if count == 0:
            # État vide si aucun mail dans le dossier courant
            self.mail_list_container.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.icons.FORWARD_TO_INBOX_ROUNDED, size=40, color=ft.colors.GREY_600),
                        ft.Text("Dossier vide", size=13, color=ft.colors.GREY_500, text_align=ft.TextAlign.CENTER)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER),
                    expand=True,
                    padding=40
                )
            )
        
        self.update()

    def _on_card_hover(self, e):
        # Effet visuel au survol des cartes
        if e.control.bgcolor != SELECTED_COLOR:
            e.control.bgcolor = HOVER_COLOR if e.data == "true" else "#242426"
            e.control.update()

    def _afficher_placeholder_lecture(self, message):
        """Affiche un bel écran vide d'attente dans la zone de lecture."""
        self.reader_content.controls.clear()
        self.reader_content.alignment = ft.MainAxisAlignment.CENTER
        self.reader_content.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.reader_content.controls.extend([
            ft.Icon(ft.icons.EMAIL_OUTLINED, size=64, color=ft.colors.GREY_700),
            ft.Container(height=10),
            ft.Text(message, size=14, color=ft.colors.GREY_500, text_align=ft.TextAlign.CENTER)
        ])

    def ouvrir_lecture(self, mail):
        """Affiche et marque comme lu le mail sélectionné."""
        self.selected_mail = mail
        mail["lu"] = True  # Passage automatique en 'lu'
        if hasattr(self.app, "save_data"): self.app.save_data()

        # Rafraîchir la liste pour enlever le gras/la puce bleue du mail lu
        self.refresh_mail_list()

        self.reader_content.controls.clear()
        self.reader_content.alignment = ft.MainAxisAlignment.START
        self.reader_content.horizontal_alignment = ft.CrossAxisAlignment.START

        # Boutons d'actions contextuels du mail
        action_buttons = ft.Row(spacing=10)
        
        if mail.get("dossier") == "trash":
            # Si dans la corbeille : Restaurer ou Supprimer à jamais
            action_buttons.controls.extend([
                ft.TextButton("🔄 Restaurer", on_click=lambda e: self.restaurer_mail(mail)),
                ft.ElevatedButton("🗑️ Supprimer définitivement", on_click=lambda e: self.supprimer_definitivement(mail), bgcolor=ft.colors.RED_800, color=ft.colors.WHITE)
            ])
        else:
            # Si dossier normal : Répondre ou Mettre à la corbeille
            action_buttons.controls.extend([
                ft.ElevatedButton("↩️ Répondre", on_click=lambda e: self.ouvrir_redaction(prefill_to=mail.get("expediteur"), prefill_subject=f"Re: {mail.get('sujet')}")),
                ft.TextButton("🗑️ Déplacer à la corbeille", icon=ft.icons.DELETE_OUTLINE, icon_color=ft.colors.RED_400, on_click=lambda e: self.supprimer_mail(mail), style=ft.ButtonStyle(color=ft.colors.RED_400))
            ])

        # Construction de la fiche de lecture propre
        self.reader_content.controls.extend([
            ft.Row([
                ft.Column([
                    ft.Text(mail.get("sujet", "(Sans sujet)"), size=22, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE),
                    ft.Text(f"De : {mail.get('expediteur')}  ◆  À : {mail.get('destinataire', 'vous@entreprise.com')}", size=12, color=ft.colors.GREY_400),
                ], expand=True),
                ft.Text(mail.get("date", ""), size=12, color=ft.colors.GREY_500)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(color="#2A2A2E", height=30),
            
            # Corps du message scrollable
            ft.Container(
                content=ft.Column([
                    ft.Text(mail.get("contenu", "Aucun contenu."), size=14, color=ft.colors.GREY_200, selectable=True)
                ], scroll=ft.ScrollMode.AUTO),
                expand=True
            ),
            ft.Divider(color="#2A2A2E", height=30),
            action_buttons
        ])
        self.update()

    def ouvrir_redaction(self, prefill_to="", prefill_subject=""):
        """Bascule la zone centrale droite en éditeur de mail professionnel."""
        self.selected_mail = None
        self.refresh_mail_list()  # Dé-sélectionne visuellement la liste

        self.txt_to = ft.TextField(label="À (Adresse destinataire)", value=prefill_to, bgcolor="#141416", border_radius=6, border_color="#2A2A2E")
        self.txt_subject = ft.TextField(label="Sujet", value=prefill_subject, bgcolor="#141416", border_radius=6, border_color="#2A2A2E")
        self.txt_body = ft.TextField(label="Votre message...", value="", multiline=True, min_lines=12, max_lines=20, bgcolor="#141416", border_radius=6, border_color="#2A2A2E", hint_text="Écrivez votre texte ici...")

        self.reader_content.controls.clear()
        self.reader_content.alignment = ft.MainAxisAlignment.START
        self.reader_content.horizontal_alignment = ft.CrossAxisAlignment.START

        self.reader_content.controls.extend([
            ft.Text("📝 Nouveau Message", size=20, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE),
            ft.Container(height=10),
            self.txt_to,
            self.txt_subject,
            self.txt_body,
            ft.Container(height=15),
            ft.Row([
                ft.ElevatedButton("🚀 Envoyer le mail", bgcolor=self.accent_color, color=ft.colors.WHITE, on_click=lambda e: self.envoyer_mail()),
                ft.TextButton("Annuler", on_click=lambda e: self._afficher_placeholder_lecture("Sélectionnez un message pour le lire"))
            ], spacing=10)
        ])
        self.update()

    def envoyer_mail(self):
        """Valide et simule l'envoi du courrier électronique."""
        dest = self.txt_to.value.strip()
        sujet = self.txt_subject.value.strip() or "(Sans sujet)"
        corps = self.txt_body.value.strip()

        if not dest:
            self.show_snack("Veuillez indiquer un destinataire.", is_error=True)
            return
        if not corps:
            self.show_snack("Le corps du message ne peut pas être vide.", is_error=True)
            return

        # Construction de l'objet Mail
        nouveau_mail = {
            "sujet": sujet,
            "expediteur": "vous@entreprise.com",
            "destinataire": dest,
            "contenu": corps,
            "dossier": "sent",
            "date": datetime.now().strftime("%d/%m, %H:%M"),
            "lu": True
        }

        # Injection dans la liste de l'application
        if not hasattr(self.app, "mails"): self.app.mails = []
        self.app.mails.insert(0, nouveau_mail) # Ajout en haut de liste
        if hasattr(self.app, "save_data"): self.app.save_data()

        self.show_snack("Le message a été envoyé avec succès ! ✈️")
        self.switch_folder("📤 Envoyés")

    def supprimer_mail(self, mail):
        """Envoie le mail dans le dossier Corbeille."""
        mail["dossier"] = "trash"
        if hasattr(self.app, "save_data"): self.app.save_data()
        self.refresh_mail_list()
        self._afficher_placeholder_lecture("Message déplacé dans la corbeille.")
        self.update()

    def restaurer_mail(self, mail):
        """Restaure un mail depuis la corbeille vers la boîte de réception."""
        mail["dossier"] = "inbox"
        if hasattr(self.app, "save_data"): self.app.save_data()
        self.refresh_mail_list()
        self._afficher_placeholder_lecture("Message restauré vers la boîte de réception.")
        self.update()

    def supprimer_definitivement(self, mail):
        """Efface définitivement le dictionnaire de la mémoire."""
        if hasattr(self.app, "mails") and mail in self.app.mails:
            self.app.mails.remove(mail)
            if hasattr(self.app, "save_data"): self.app.save_data()
        self.refresh_mail_list()
        self._afficher_placeholder_lecture("Message supprimé définitivement.")
        self.update()

    def show_snack(self, message, is_error=False):
        self.app.page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.colors.RED_700 if is_error else ft.colors.GREEN_700
        )
        self.app.page.snack_bar.open = True
        self.app.page.update()