import flet as ft
from pathlib import Path


def safe_float(val):
    """Convertit proprement n'importe quelle chaîne financière en float (gère les €, espaces et virgules)."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    try:
        s = (
            str(val)
            .replace("€", "")
            .replace(" ", "")
            .replace("\xa0", "")
            .replace(",", ".")
            .strip()
        )
        return float(s) if s else 0.0
    except ValueError:
        return 0.0


class DashboardView(ft.Container):
    """Vue Tableau de bord 100% complète, réactive et optimisée pour smartphone et PC."""

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.expand = True
        self.padding = 10

        self.accent_color = "#2B719E"
        if hasattr(self.app, "entreprise") and isinstance(
            self.app.entreprise, dict
        ):
            self.accent_color = self.app.entreprise.get(
                "accent_color", "#2B719E"
            )

        self._build_interface()

    def _build_interface(self):
        if hasattr(self.app, "load_data"):
            self.app.load_data()

        # 1. CALCULS DES DONNÉES EN TEMPS RÉEL
        factures_list = getattr(self.app, "factures", [])

        factures_valides = [
            f
            for f in factures_list
            if str(f.get("statut", "")).lower()
            in [
                "payée",
                "validée",
                "encaissée",
                "payee",
                "encaissee",
                "payé",
                "valide",
            ]
        ]

        total_ca = sum(
            safe_float(f.get("total_ttc", f.get("montant_ttc", 0)))
            for f in factures_valides
        )
        nb_factures = len(factures_valides)
        panier_moyen = total_ca / nb_factures if nb_factures > 0 else 0.0

        def card_hover(e):
            try:
                e.control.border = ft.border.all(
                    1.5, self.accent_color if e.data == "true" else "#2A2A32"
                )
                e.control.update()
            except Exception:
                pass

        # 2. CARTES KPI DESIGN PREMIUM
        def create_kpi_card(title, value, icon, icon_color, subtitle=None):
            return ft.Container(
                bgcolor="#1E1E22",
                border_radius=14,
                padding=16,
                border=ft.border.all(1, "#2A2A32"),
                on_hover=card_hover,
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    title,
                                    size=11,
                                    color="#AEAEB2",
                                    weight=ft.FontWeight.W_600,
                                ),
                                ft.Text(
                                    value,
                                    size=20,
                                    weight=ft.FontWeight.BOLD,
                                    color="white",
                                ),
                                *(
                                    [
                                        ft.Text(
                                            subtitle, size=11, color="#34D399"
                                        )
                                    ]
                                    if subtitle
                                    else []
                                ),
                            ],
                            spacing=4,
                            expand=True,
                        ),
                        ft.Container(
                            content=ft.Icon(icon, color=icon_color, size=22),
                            bgcolor="#2A2A32",
                            padding=10,
                            border_radius=10,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )

        card_ca = create_kpi_card(
            title="CHIFFRE D'AFFAIRES ENCAISSÉ",
            value=f"{total_ca:,.2f} €".replace(",", " "),
            icon="attach_money",
            icon_color="green",
            subtitle="📈 Objectifs en bonne voie" if total_ca > 0 else None,
        )

        card_panier = create_kpi_card(
            title="PANIER MOYEN CLIENT",
            value=f"{panier_moyen:,.2f} €".replace(",", " "),
            icon="shopping_bag",
            icon_color=self.accent_color,
        )

        card_volume = create_kpi_card(
            title="FACTURES ENCAISSÉES",
            value=f"{nb_factures} document(s)",
            icon="analytics",
            icon_color="orange",
        )

        # 3. RACCOURCIS EN GRILLE ADAPTATIVE (STCKÉS SUR MOBILE)
        def create_shortcut_btn(text, icon, target_view):
            def _on_hover(e):
                try:
                    e.control.bgcolor = (
                        "#1A1A1E" if e.data == "true" else "#141416"
                    )
                    e.control.update()
                except Exception:
                    pass

            return ft.Container(
                bgcolor="#141416",
                padding=12,
                border_radius=10,
                border=ft.border.all(1, "#242428"),
                on_click=lambda e: self.app.navigate_to(target_view),
                on_hover=_on_hover,
                content=ft.Row(
                    [
                        ft.Icon(icon, color=self.accent_color, size=18),
                        ft.Text(
                            text,
                            size=13,
                            weight=ft.FontWeight.W_600,
                            color="white",
                        ),
                    ],
                    spacing=10,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            )

        shortcuts_box = ft.Container(
            bgcolor="#1E1E22",
            padding=15,
            border_radius=12,
            border=ft.border.all(1, "#2A2A32"),
            content=ft.Column(
                [
                    ft.Text(
                        "⚡ RACCOURCIS ET ACTIONS RAPIDES",
                        size=12,
                        color="#AEAEB2",
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.ResponsiveRow(
                        [
                            ft.Column(
                                [
                                    create_shortcut_btn(
                                        "Nouvelle Facture", "add", "NouvelleFacture"
                                    )
                                ],
                                col={"sm": 12, "md": 4},
                            ),
                            ft.Column(
                                [
                                    create_shortcut_btn(
                                        "Suivi TVA & Charges",
                                        "account_balance_wallet",
                                        "Comptabilite",
                                    )
                                ],
                                col={"sm": 12, "md": 4},
                            ),
                            ft.Column(
                                [
                                    create_shortcut_btn(
                                        "Consulter l'Agenda",
                                        "calendar_month",
                                        "Agenda",
                                    )
                                ],
                                col={"sm": 12, "md": 4},
                            ),
                        ],
                        spacing=10,
                    ),
                ],
                spacing=10,
            ),
        )

        # 4. PANNEAU DE CONVERSATION DE L'ASSISTANT IA
        self.chat_response = ft.Text(
            "Bonjour ! Que puis-je analyser pour vous aujourd'hui ? (Ex: 'Quel est mon CA ?')",
            color="#AEAEB2",
            size=13,
        )
        self.chat_input = ft.TextField(
            hint_text="Posez votre question sur vos finances...",
            expand=True,
            border_color="#2A2A32",
            focused_border_color=self.accent_color,
            text_size=13,
            height=45,
            content_padding=12,
            text_style=ft.TextStyle(color="white"),
            on_submit=self._analyser_requete,
        )

        chat_box = ft.Container(
            bgcolor="#1E1E22",
            padding=15,
            border_radius=12,
            border=ft.border.all(1, "#2A2A32"),
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Icon(
                                    "auto_awesome",
                                    color=self.accent_color,
                                    size=18,
                                ),
                                bgcolor="#2A2A32",
                                padding=6,
                                border_radius=6,
                            ),
                            ft.Text(
                                "ASSISTANT VIRTUEL IA",
                                weight=ft.FontWeight.BOLD,
                                size=13,
                                color="white",
                            ),
                        ],
                        spacing=10,
                    ),
                    ft.Divider(color="#2A2A32", height=10),
                    ft.Container(
                        content=self.chat_response,
                        bgcolor="#141416",
                        padding=12,
                        border_radius=8,
                        height=60,
                    ),
                    ft.Row(
                        [
                            self.chat_input,
                            ft.IconButton(
                                icon="navigate_next",
                                icon_color="white",
                                bgcolor=self.accent_color,
                                height=45,
                                width=45,
                                style=ft.ButtonStyle(
                                    shape=ft.RoundedRectangleBorder(radius=8)
                                ),
                                on_click=self._analyser_requete,
                            ),
                        ],
                        spacing=10,
                    ),
                ],
                spacing=10,
            ),
        )

        # 5. ASSEMBLAGE DE LA STRUCTURE PRINCIPALE
        self.content = ft.Column(
            controls=[
                ft.Column(
                    [
                        ft.Text(
                            "Bonjour 👋",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color="white",
                        ),
                        ft.Text(
                            "Aperçu en temps réel de votre activité commerciale.",
                            size=12,
                            color="#AEAEB2",
                        ),
                    ],
                    spacing=2,
                ),
                ft.ResponsiveRow(
                    [
                        ft.Column([card_ca], col={"sm": 12, "md": 4}),
                        ft.Column([card_panier], col={"sm": 12, "md": 4}),
                        ft.Column([card_volume], col={"sm": 12, "md": 4}),
                    ],
                    spacing=12,
                ),
                shortcuts_box,
                chat_box,
            ],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=15,
        )

    def _analyser_requete(self, e):
        query = (
            self.chat_input.value.lower().strip()
            if self.chat_input.value
            else ""
        )
        if not query:
            return

        if hasattr(self.app, "load_data"):
            self.app.load_data()

        factures_list = getattr(self.app, "factures", [])
        factures_valides = [
            f
            for f in factures_list
            if str(f.get("statut", "")).lower()
            in [
                "payée",
                "validée",
                "encaissée",
                "payee",
                "encaissee",
                "payé",
            ]
        ]

        if "ca" in query or "chiffre d'affaires" in query:
            total_ca = sum(
                safe_float(f.get("total_ttc", f.get("montant_ttc", 0)))
                for f in factures_valides
            )
            self.chat_response.value = f"Votre Chiffre d'Affaires total encaissé s'élève à précisément {total_ca:,.2f} €.".replace(
                ",", " "
            )
            self.chat_response.color = "green"
        elif "panier" in query:
            total_ca = sum(
                safe_float(f.get("total_ttc", f.get("montant_ttc", 0)))
                for f in factures_valides
            )
            nb = len(factures_valides)
            pm = total_ca / nb if nb > 0 else 0.0
            self.chat_response.value = f"Votre panier moyen actuel est de {pm:,.2f} € pour {nb} facture(s) encaissée(s).".replace(
                ",", " "
            )
            self.chat_response.color = self.accent_color
        else:
            self.chat_response.value = "Je comprends les requêtes concernant votre 'CA' ou votre 'Panier Moyen'. Que voulez-vous savoir ?"
            self.chat_response.color = "#AEAEB2"

        self.chat_input.value = ""
        if self.page:
            self.page.update()
        else:
            self.update()
