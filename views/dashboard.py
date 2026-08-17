import flet as ft
from pathlib import Path

def safe_float(val):
    """Convertit proprement n'importe quelle chaîne financière en float (gère les €, espaces et virgules)."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    try:
        s = str(val).replace("€", "").replace(" ", "").replace("\xa0", "").replace(",", ".").strip()
        return float(s) if s else 0.0
    except ValueError:
        return 0.0

class DashboardView(ft.Container):
    def __init__(self, app):
        super().__init__(expand=True)
        self.app = app
        
        # Récupération de la couleur d'accentuation depuis les paramètres de l'entreprise
        self.accent_color = "#2B719E"
        if hasattr(self.app, "entreprise") and isinstance(self.app.entreprise, dict):
            self.accent_color = self.app.entreprise.get("accent_color", "#2B719E")
            
        self.setup_ui()

    def setup_ui(self):
        # 🟢 CORRECTION 1 : Force le rechargement des données depuis database.json avant le calcul
        if hasattr(self.app, "load_data"):
            self.app.load_data()

        # 1. CALCULS DES DONNÉES EN TEMPS RÉEL
        factures_list = getattr(self.app, "factures", [])
        
        # 🟢 CORRECTION 2 : Filtrage robuste insensible à la casse et aux accents fréquents
        factures_valides = [
            f for f in factures_list 
            if str(f.get("statut", "")).lower() in ["payée", "validée", "encaissée", "payee", "encaissee", "payé", "valide"]
        ]
        
        # 🟢 CORRECTION 3 : Prise en charge de 'total_ttc' ou 'montant_ttc' comme dans facturation.py
        total_ca = sum(safe_float(f.get("total_ttc", f.get("montant_ttc", 0))) for f in factures_valides)
        nb_factures = len(factures_valides)
        panier_moyen = total_ca / nb_factures if nb_factures > 0 else 0.0

        # Fonction pour l'effet visuel dynamique au survol des cartes (Hover effect)
        def card_hover(e):
            e.control.border = ft.border.all(1.5, self.accent_color if e.data == "true" else "#2A2A32")
            e.control.update()

        # 2. CONSTRUCTEUR DE CARTES KPI DESIGN PREMIUM
        def create_kpi_card(title, value, icon, icon_color, subtitle=None):
            return ft.Container(
                bgcolor="#1E1E22",
                border_radius=14,
                padding=18,
                border=ft.border.all(1, "#2A2A32"),
                on_hover=card_hover,
                content=ft.Row([
                    ft.Column([
                        ft.Text(title, size=11, color="#AEAEB2", weight=ft.FontWeight.W_600),
                        ft.Text(value, size=22, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE),
                        *( [ft.Text(subtitle, size=11, color="#34D399")] if subtitle else [] )
                    ], spacing=4, expand=True),
                    ft.Container(
                        content=ft.Icon(icon, color=icon_color, size=22),
                        bgcolor=ft.colors.with_opacity(0.1, icon_color),
                        padding=12,
                        border_radius=10
                    )
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            )

        # Génération des 3 cartes KPI fondamentales
        card_ca = create_kpi_card(
            title="CHIFFRE D'AFFAIRES ENCAISSÉ",
            value=f"{total_ca:,.2f} €".replace(",", " "),
            icon=ft.icons.ATTACH_MONEY,
            icon_color=ft.colors.GREEN_400,
            subtitle="📈 Objectifs en bonne voie" if total_ca > 0 else None
        )

        card_panier = create_kpi_card(
            title="PANIER MOYEN CLIENT",
            value=f"{panier_moyen:,.2f} €".replace(",", " "),
            icon=ft.icons.SHOPPING_BAG,
            icon_color=self.accent_color
        )

        card_volume = create_kpi_card(
            title="FACTURES ENCAISSÉES",
            value=f"{nb_factures} document(s)",
            icon=ft.icons.ANALYTICS,
            icon_color=ft.colors.ORANGE_400
        )

        # 3. CONSTRUCTEUR DES BOUTONS DE NAVIGATION RAPIDE (QUICK ACTIONS)
        def create_shortcut_btn(text, icon, target_view):
            return ft.Container(
                bgcolor="#141416",
                padding=12,
                border_radius=10,
                border=ft.border.all(1, "#242428"),
                on_click=lambda e: self.app.navigate_to(target_view),
                on_hover=lambda e: setattr(e.control, "bgcolor", "#1A1A1E" if e.data == "true" else "#141416") or e.control.update(),
                content=ft.Row([
                    ft.Icon(icon, color=self.accent_color, size=18),
                    ft.Text(text, size=13, weight=ft.FontWeight.W_600, color=ft.colors.WHITE)
                ], spacing=10, alignment=ft.MainAxisAlignment.CENTER),
                expand=True
            )

        shortcuts_box = ft.Container(
            bgcolor="#1E1E22",
            padding=15,
            border_radius=12,
            border=ft.border.all(1, "#2A2A32"),
            content=ft.Column([
                ft.Text("⚡ RACCOURCIS ET ACTIONS RAPIDES", size=12, color="#AEAEB2", weight=ft.FontWeight.BOLD),
                ft.Row([
                    create_shortcut_btn("Nouvelle Facture", ft.icons.ADD, "NouvelleFacture"),
                    create_shortcut_btn("Suivi TVA & Charges", ft.icons.ACCOUNT_BALANCE_WALLET, "Comptabilite"),
                    create_shortcut_btn("Consulter l'Agenda", ft.icons.CALENDAR_MONTH, "Agenda"),
                ], spacing=12)
            ], spacing=10)
        )

        # 4. PANNEAU DE CONVERSATION DE L'ASSISTANT IA
        self.chat_response = ft.Text(
            "Bonjour Francky ! Que puis-je analyser pour vous aujourd'hui ? (Ex: 'Quel est mon CA ?')",
            color="#AEAEB2",
            size=13
        )
        self.chat_input = ft.TextField(
            hint_text="Posez votre question sur vos finances...",
            expand=True,
            border_color="#2A2A32",
            focused_border_color=self.accent_color,
            text_size=13,
            height=45,
            content_padding=12,
            text_style=ft.TextStyle(color=ft.colors.WHITE),
            on_submit=self._analyser_requete
        )

        chat_box = ft.Container(
            bgcolor="#1E1E22",
            padding=20,
            border_radius=12,
            border=ft.border.all(1, "#2A2A32"),
            content=ft.Column([
                ft.Row([
                    ft.Container(
                        content=ft.Icon(ft.icons.AUTO_AWESOME, color=self.accent_color, size=18),
                        bgcolor=ft.colors.with_opacity(0.1, self.accent_color),
                        padding=6,
                        border_radius=6
                    ),
                    ft.Text("ASSISTANT VIRTUEL IA", weight=ft.FontWeight.BOLD, size=13, color=ft.colors.WHITE)
                ], spacing=10),
                ft.Divider(color="#2A2A32", height=15),
                ft.Container(
                    content=self.chat_response,
                    bgcolor="#141416",
                    padding=12,
                    border_radius=8,
                    height=70,
                ),
                ft.Row([
                    self.chat_input,
                    ft.IconButton(
                        icon=ft.icons.NAVIGATE_NEXT,
                        icon_color=ft.colors.WHITE,
                        bgcolor=self.accent_color,
                        height=45,
                        width=45,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                        on_click=self._analyser_requete
                    )
                ], spacing=10)
            ], spacing=10)
        )

        # 5. ASSEMBLAGE DE LA STRUCTURE COMPLÈTE
        self.content = ft.Container(
            padding=20,
            content=ft.Column(
                controls=[
                    ft.Row([
                        ft.Column([
                            ft.Text("Bonjour 👋", size=28, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE),
                            ft.Text("Voici un aperçu en temps réel de votre activité commerciale.", size=13, color="#AEAEB2")
                        ], spacing=2)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    
                    ft.Container(height=10),
                    
                    ft.ResponsiveRow([
                        ft.Column([card_ca], col={"sm": 12, "md": 4}),
                        ft.Column([card_panier], col={"sm": 12, "md": 4}),
                        ft.Column([card_volume], col={"sm": 12, "md": 4}),
                    ], spacing=15),
                    
                    ft.Container(height=10),
                    shortcuts_box,
                    ft.Container(height=10),
                    chat_box
                 ],
                 scroll=ft.ScrollMode.AUTO,
                 expand=True,
                 spacing=10
              )
          )

    def _analyser_requete(self, e):
        query = self.chat_input.value.lower().strip()
        if not query: 
            return
        
        # 🟢 CORRECTION EXTRA : Force aussi la mise à jour pour l'IA intégrée au survol
        if hasattr(self.app, "load_data"):
            self.app.load_data()
        
        factures_list = getattr(self.app, "factures", [])
        factures_valides = [
            f for f in factures_list 
            if str(f.get("statut", "")).lower() in ["payée", "validée", "encaissée", "payee", "encaissee", "payé"]
        ]

        if "ca" in query or "chiffre d'affaires" in query:
            total_ca = sum(safe_float(f.get("total_ttc", f.get("montant_ttc", 0))) for f in factures_valides)
            self.chat_response.value = f"Votre Chiffre d'Affaires total encaissé s'élève à précisément {total_ca:,.2f} €.".replace(",", " ")
            self.chat_response.color = ft.colors.GREEN_400
        elif "panier" in query:
            total_ca = sum(safe_float(f.get("total_ttc", f.get("montant_ttc", 0))) for f in factures_valides)
            nb = len(factures_valides)
            pm = total_ca / nb if nb > 0 else 0.0
            self.chat_response.value = f"Votre panier moyen actuel est de {pm:,.2f} € pour {nb} facture(s) encaissée(s).".replace(",", " ")
            self.chat_response.color = self.accent_color
        else:
            self.chat_response.value = "Je comprends les requêtes concernant votre 'CA' ou votre 'Panier Moyen'. Que voulez-vous savoir ?"
            self.chat_response.color = "#AEAEB2"
            
        self.chat_input.value = ""
        self.update()