import flet as ft
from datetime import datetime
from pathlib import Path

CARD_COLOR = "#1E1E22"
PRIMARY_COLOR = "#2B719E"
SUCCESS_COLOR = "#10B981"
WARNING_COLOR = "#F59E0B"
ERROR_COLOR = "#EF4444"

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

def parse_date(date_str):
    """Parse de manière robuste les chaînes de dates sous différents formats usuels."""
    if not date_str:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(str(date_str).strip().split()[0], fmt)
        except ValueError:
            continue
    return None

class FinanceView(ft.Container):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.expand = True
        self.padding = 15

        # Récupération sécurisée des paramètres de base de l'entreprise
        self.entreprise_data = getattr(self.app, "entreprise", {})
        if isinstance(self.entreprise_data, dict):
            self.date_creation = self.entreprise_data.get("date_creation", datetime.now().strftime("%d/%m/%Y"))
            self.activite = self.entreprise_data.get("type_activite", "Services")
        else:
            self.date_creation = datetime.now().strftime("%d/%m/%Y")
            self.activite = "Services"

        self._build_interface()

    def did_mount(self):
        """🟢 AUTOMATISATION : Se déclenche dès l'affichage pour actualiser les données réelles."""
        self.update_dashboard()

    def _build_interface(self):
        # --- 1. BLOC CONFIGURATION ---
        self.tf_date = ft.TextField(label="Date création", value=self.date_creation, width=140, height=40, text_size=13)
        self.dd_type = ft.Dropdown(
            label="Activité",
            options=[ft.dropdown.Option("Services"), ft.dropdown.Option("Vente")],
            value=self.activite,
            width=140,
            height=40,
            text_size=13
        )
        
        config_card = ft.Container(
            content=ft.Row([
                ft.Row([self.tf_date, self.dd_type], spacing=10),
                ft.ElevatedButton(
                    "🔄 Actualiser",
                    bgcolor=PRIMARY_COLOR,
                    color=ft.colors.WHITE,
                    icon=ft.icons.REFRESH,
                    on_click=lambda _: self.update_dashboard(),
                    height=40
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            bgcolor=CARD_COLOR,
            border=ft.border.all(1, "#2A2A2E"),
            border_radius=8,
            padding=10
        )

        # --- 2. INITIALISATION DES ÉTIQUETTES FINANCIÈRES ---
        self.lbl_ca_mensuel = ft.Text("0.00 €", size=15, weight=ft.FontWeight.BOLD)
        self.lbl_ca_annuel = ft.Text("0.00 €", size=15, weight=ft.FontWeight.BOLD)
        self.lbl_seuil = ft.Text("0.00 €", size=15, weight=ft.FontWeight.BOLD)
        self.lbl_reste = ft.Text("0.00 €", size=15, weight=ft.FontWeight.BOLD)
        
        self.lbl_urssaf_mensuel = ft.Text("0.00 €", size=15, weight=ft.FontWeight.BOLD, color=ERROR_COLOR)
        self.lbl_urssaf_annuel = ft.Text("0.00 €", size=15, weight=ft.FontWeight.BOLD, color="#DC2626")
        
        self.lbl_bc_total = ft.Text("0.00 €", size=15, weight=ft.FontWeight.BOLD, color=PRIMARY_COLOR)
        self.lbl_bl_total = ft.Text("0.00 €", size=15, weight=ft.FontWeight.BOLD, color=WARNING_COLOR)
        self.lbl_charges = ft.Text("0.00 €", size=15, weight=ft.FontWeight.BOLD, color=ft.colors.RED_400)
        self.lbl_ca_net = ft.Text("0.00 €", size=15, weight=ft.FontWeight.BOLD, color=SUCCESS_COLOR)

        # --- 3. BLOC PROGRESSION ---
        self.progress_bar = ft.ProgressBar(value=0.0, color=SUCCESS_COLOR, bgcolor="#2A2A2E", height=8)
        self.lbl_status = ft.Text("---", size=11, italic=True)
        
        progression_card = ft.Container(
            content=ft.Column([
                ft.Text("Progression vers le plafond légal :", size=11, color=ft.colors.GREY_400),
                self.progress_bar,
                self.lbl_status
            ], spacing=4),
            bgcolor="transparent"
        )

        # --- 4. CONFIGURATION DE LA COLONNE GAUCHE (STATISTIQUES COMPACTES) ---
        left_column = ft.Column(
            controls=[
                ft.Row([self.create_stat_card("CA Ce mois-ci", self.lbl_ca_mensuel), self.create_stat_card("URSSAF à verser (Mois)", self.lbl_urssaf_mensuel)], spacing=10),
                ft.Row([self.create_stat_card("CA Année en cours", self.lbl_ca_annuel), self.create_stat_card("URSSAF Total (Année)", self.lbl_urssaf_annuel)], spacing=10),
                ft.Row([self.create_stat_card("Plafond (Prorata)", self.lbl_seuil), self.create_stat_card("Reste à facturer", self.lbl_reste)], spacing=10),
                ft.Row([self.create_stat_card("Volume Bons Commande (BC)", self.lbl_bc_total), self.create_stat_card("Volume Bons Livraison (BL)", self.lbl_bl_total)], spacing=10),
                ft.Row([self.create_stat_card("Total Charges / Dépenses", self.lbl_charges), self.create_stat_card("📈 CA Net Réel (Déduit)", self.lbl_ca_net)], spacing=10),
                ft.Container(height=5),
                progression_card
            ],
            spacing=8,
            expand=True
        )

        # --- 5. CONFIGURATION DE LA COLONNE DROITE (GRAPHIQUE HISTORIQUE) ---
        self.chart_container = ft.Container(content=ft.Text("Aucune donnée disponible", color=ft.colors.GREY_400), expand=True, alignment=ft.alignment.center)
        
        graph_card = ft.Container(
            content=ft.Column([
                ft.Text("📈 Cotisations mensuelles URSSAF prévisionnelles", size=13, weight=ft.FontWeight.BOLD, color=PRIMARY_COLOR),
                ft.Divider(height=1, color="#2A2A2E"),
                self.chart_container
            ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, expand=True),
            bgcolor=CARD_COLOR,
            border=ft.border.all(1, "#2A2A2E"),
            border_radius=12,
            padding=15,
            expand=True
        )

        # --- 6. ASSEMBLAGE ---
        dashboard_body = ft.Row(
            controls=[
                ft.Container(content=left_column, expand=11),
                ft.Container(content=graph_card, expand=9)
            ],
            spacing=15,
            expand=True
        )

        self.content = ft.Column(
            controls=[
                ft.Row([ft.Text("📊 Tableau de Bord Financier & URSSAF", size=22, weight=ft.FontWeight.BOLD)]),
                config_card,
                dashboard_body
            ],
            spacing=15,
            expand=True
        )

    def create_stat_card(self, title, label_control):
        """Génère une micro-carte financière compacte."""
        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=10, weight=ft.FontWeight.BOLD, color="#A0A0A0", no_wrap=True),
                label_control
            ], spacing=2, alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=CARD_COLOR,
            border=ft.border.all(1, "#2A2A2E"),
            border_radius=8,
            padding=10,
            expand=True,
            height=68
        )

    def update_dashboard(self):
        """🟢 LOGIQUE TECHNIQUE DE MISE À JOUR EN TEMPS RÉEL (ANTI-BUG)"""
        # 1. Rechargement forcé de la base de données
        if hasattr(self.app, "load_data"):
            self.app.load_data()

        now = datetime.now()
        ca_mensuel = 0.0
        ca_annuel = 0.0
        months_ca = [0.0] * 12

        # 2. Extraction sécurisée et filtrage des factures
        factures_list = getattr(self.app, "factures", [])
        factures_valides = [
            f for f in factures_list
            if str(f.get("statut", "")).lower() in ["payée", "validée", "encaissée", "payee", "encaissee", "payé", "valide"]
        ]

        # 3. Répartition temporelle du Chiffre d'Affaires
        for f in factures_valides:
            # Sécurité multi-clés : total_ttc ou montant_ttc ou alternatives HT
            montant = safe_float(f.get("total_ttc", f.get("montant_ttc", f.get("total_ht", f.get("montant_ht", 0)))))
            d_str = f.get("date_paiement", f.get("date_creation", ""))
            dt = parse_date(d_str)

            if dt and dt.year == now.year:
                ca_annuel += montant
                months_ca[dt.month - 1] += montant
                if dt.month == now.month:
                    ca_mensuel += montant
            elif not dt:
                # Fallback de secours si la date n'est pas lisible
                ca_annuel += montant

        # 4. Détermination des taux URSSAF et plafonds légaux (Micro-entreprise France)
        is_vente = self.dd_type.value == "Vente"
        taux_urssaf = 0.123 if is_vente else 0.212  # 12.3% Vente / 21.2% Prestation de Services (BNC/BIC)
        plafond_base = 188700.0 if is_vente else 77700.0

        # Calcul intelligent du prorata temporis si création de l'entreprise l'année en cours
        plafond = plafond_base
        try:
            date_crea = parse_date(self.tf_date.value)
            if date_crea and date_crea.year == now.year:
                jours_restants = (datetime(now.year, 12, 31) - date_crea).days + 1
                jours_annee = 366 if (now.year % 4 == 0 and (now.year % 100 != 0 or now.year % 400 == 0)) else 365
                plafond = (plafond_base * jours_restants) / jours_annee
        except Exception:
            pass

        # 5. Calculs des charges annexes, BC et BL
        urssaf_mensuel = ca_mensuel * taux_urssaf
        urssaf_annuel = ca_annuel * taux_urssaf
        reste_a_facturer = max(0.0, plafond - ca_annuel)
        
        total_bc = sum(safe_float(b.get("total_ttc", b.get("montant_ttc", 0))) for b in getattr(self.app, "bons_commande", []))
        total_bl = sum(safe_float(l.get("total_ttc", l.get("montant_ttc", 0))) for l in getattr(self.app, "bons_livraison", []))
        
        # Récupération dynamique des charges (si implémenté dans l'app)
        total_charges = sum(safe_float(c.get("montant", 0)) for c in getattr(self.app, "charges", []))
        ca_net = ca_annuel - urssaf_annuel - total_charges

        # 6. Assignation graphique des indicateurs
        self.lbl_ca_mensuel.value = f"{ca_mensuel:,.2f} €".replace(",", " ")
        self.lbl_ca_annuel.value = f"{ca_annuel:,.2f} €".replace(",", " ")
        self.lbl_seuil.value = f"{plafond:,.2f} €".replace(",", " ")
        self.lbl_reste.value = f"{reste_a_facturer:,.2f} €".replace(",", " ")
        self.lbl_urssaf_mensuel.value = f"{urssaf_mensuel:,.2f} €".replace(",", " ")
        self.lbl_urssaf_annuel.value = f"{urssaf_annuel:,.2f} €".replace(",", " ")
        self.lbl_bc_total.value = f"{total_bc:,.2f} €".replace(",", " ")
        self.lbl_bl_total.value = f"{total_bl:,.2f} €".replace(",", " ")
        self.lbl_charges.value = f"{total_charges:,.2f} €".replace(",", " ")
        self.lbl_ca_net.value = f"{ca_net:,.2f} €".replace(",", " ")

        # Gestion de la barre de progression vers le plafond
        pct_progression = min(1.0, ca_annuel / plafond) if plafond > 0 else 0.0
        self.progress_bar.value = pct_progression
        self.lbl_status.value = f"{pct_progression * 100:.1f}% du plafond légal atteint ({reste_a_facturer:,.2f} € disponibles)"

        # 7. Génération dynamique du graphique à barres URSSAF
        bar_groups = []
        for i in range(12):
            monthly_tax = months_ca[i] * taux_urssaf
            bar_groups.append(
                ft.BarChartGroup(
                    x=i,
                    bar_rods=[
                        ft.BarChartRod(
                            from_y=0,
                            to_y=monthly_tax,
                            color=PRIMARY_COLOR if monthly_tax > 0 else ft.colors.GREY_700,
                            width=10,
                            border_radius=3
                        )
                    ]
                )
            )

        self.chart_container.content = ft.BarChart(
            bar_groups=bar_groups,
            bottom_axis=ft.ChartAxis(
                labels=[
                    ft.ChartAxisLabel(value=0, label=ft.Text("J", size=9)),
                    ft.ChartAxisLabel(value=1, label=ft.Text("F", size=9)),
                    ft.ChartAxisLabel(value=2, label=ft.Text("M", size=9)),
                    ft.ChartAxisLabel(value=3, label=ft.Text("A", size=9)),
                    ft.ChartAxisLabel(value=4, label=ft.Text("M", size=9)),
                    ft.ChartAxisLabel(value=5, label=ft.Text("J", size=9)),
                    ft.ChartAxisLabel(value=6, label=ft.Text("J", size=9)),
                    ft.ChartAxisLabel(value=7, label=ft.Text("A", size=9)),
                    ft.ChartAxisLabel(value=8, label=ft.Text("S", size=9)),
                    ft.ChartAxisLabel(value=9, label=ft.Text("O", size=9)),
                    ft.ChartAxisLabel(value=10, label=ft.Text("N", size=9)),
                    ft.ChartAxisLabel(value=11, label=ft.Text("D", size=9)),
                ],
                labels_size=16,
            ),
            left_axis=ft.ChartAxis(labels_size=35),
            border=ft.border.all(1, "#2A2A2E"),
            expand=True
        )

        # Demande de rafraîchissement à Flet
        self.update()