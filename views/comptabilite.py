import flet as ft
from datetime import datetime

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

class ComptabiliteView(ft.Container):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.expand = True
        self.padding = 15
        
        # Récupération de la charte graphique de l'entreprise
        self.accent_color = "#2B719E"
        if hasattr(self.app, "entreprise") and isinstance(self.app.entreprise, dict):
            self.accent_color = self.app.entreprise.get("accent_color", "#2B719E")

        # Initialisation sécurisée du registre des charges
        if not hasattr(self.app, "charges"):
            self.app.charges = []

        self.setup_ui()

    def did_mount(self):
        """🟢 AUTOMATISATION : Force le rechargement réel des données dès que la vue s'affiche."""
        if hasattr(self.app, "load_data"):
            self.app.load_data()
        self._on_tab_change(None)

    def setup_ui(self):
        """Crée la structure adaptative complète de la vue Comptabilité."""
        # ─── EN-TÊTE ───
        title_text = ft.Text("📈 Comptabilité & Optimisation TVA", size=24, weight=ft.FontWeight.BOLD)
        
        self.combo_periode = ft.Dropdown(
            value="Trimestre en cours",
            options=[
                ft.dropdown.Option("Mois en cours"),
                ft.dropdown.Option("Trimestre en cours"),
                ft.dropdown.Option("Année complète")
            ],
            width=220,
            height=45,
            on_change=self._mettre_a_jour_tout
        )

        header = ft.Row(
            controls=[title_text, self.combo_periode],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

        # ─── NAVIGATION INTERNE (ONGLETS FLET) ───
        self.tabs = ft.Tabs(
            selected_index=0,
            on_change=self._on_tab_change,
            tabs=[
                ft.Tab(text="📊 Synthèse & KPIs"),
                ft.Tab(text="💸 Registre des Charges"),
                ft.Tab(text="🏛️ Assistant Déclaration CA3")
            ],
        )

        # ─── CONTENEUR CENTRAL PRINCIPAL (FLUIDE/EXPAND) ───
        self.main_container = ft.Container(
            expand=True,
            bgcolor="#1E1E20",
            border_radius=12,
            border=ft.border.all(1, "#2A2A2E"),
            padding=20
        )

        # Structure globale de la vue
        self.content = ft.Column(
            controls=[
                header,
                self.tabs,
                self.main_container
            ],
            expand=True,
            spacing=15
        )

        # Premier rendu par défaut sur l'onglet Synthèse
        self._afficher_synthese()

    def _on_tab_change(self, e):
        """Gère le basculement dynamique entre les sous-onglets."""
        idx = self.tabs.selected_index
        if idx == 0:
            self._afficher_synthese()
        elif idx == 1:
            self._afficher_registre_charges()
        elif idx == 2:
            self._afficher_assistant_ca3()
        self.update()

    def _mettre_a_jour_tout(self, e):
        """Force le rafraîchissement des calculs et de l'affichage lors du changement de période."""
        self._on_tab_change(None)

    def _calculer_metriques_financieres(self):
        """Calcule de manière sécurisée les métriques uniquement sur les pièces encaissées."""
        factures = getattr(self.app, "factures", [])
        
        # 🟢 FIX COMPTABLE : Filtrage strict sur les factures réellement encaissées/payées
        factures_valides = [
            f for f in factures
            if str(f.get("statut", "")).lower() in ["payée", "validée", "encaissée", "payee", "encaissee", "payé", "valide"]
        ]
        
        ca_ht, tva_20, tva_10, tva_5 = 0.0, 0.0, 0.0, 0.0
        
        for f in factures_valides:
            # 🟢 FIX SÉCURITÉ : Multi-clés et protection contre le crash de chaînes formatées
            total_ttc = safe_float(f.get("total_ttc", f.get("montant_ttc", f.get("ttc", 0))))
            total_ht = safe_float(f.get("total_ht", f.get("montant_ht", f.get("ht", 0))))
            tva_totale = total_ttc - total_ht
            ca_ht += total_ht
            
            taux = safe_float(f.get("taux_tva", 20))
            if taux == 20: 
                tva_20 += tva_totale
            elif taux == 10: 
                tva_10 += tva_totale
            else: 
                tva_5 += tva_totale

        tva_collectee_totale = tva_20 + tva_10 + tva_5
        tva_deductible_totale, tva_autoliquidee, total_charges_ht = 0.0, 0.0, 0.0

        for c in getattr(self.app, "charges", []):
            ht = safe_float(c.get("ht", 0))
            taux_tva = safe_float(c.get("taux", 20))
            coef_recup = safe_float(c.get("coef_recup", 100)) / 100.0
            est_autoliquide = c.get("autoliquide", False)
            tva_theorique = ht * (taux_tva / 100.0)
            total_charges_ht += ht

            if est_autoliquide:
                tva_autoliquidee += tva_theorique
                tva_deductible_totale += tva_theorique * coef_recup
            else:
                tva_deductible_totale += tva_theorique * coef_recup

        return {
            "ca_ht": ca_ht, 
            "tva_collectee": tva_collectee_totale + tva_autoliquidee,
            "tva_20": tva_20, 
            "tva_10": tva_10, 
            "tva_5": tva_5, 
            "tva_autoliquidee": tva_autoliquidee,
            "total_charges_ht": total_charges_ht, 
            "tva_deductible": tva_deductible_totale,
            "solde_tva": (tva_collectee_totale + tva_autoliquidee) - tva_deductible_totale
        }

    def _afficher_synthese(self):
        """Rend l'onglet Synthèse avec ses 3 KPI Cards fluides, son solde global et ses détails."""
        data = self._calculer_metriques_financieres()
        
        cards = []
        for title, val, color in [
            ("Chiffre d'Affaires global (HT)", f"{data['ca_ht']:.2f} €", ft.colors.WHITE),
            ("Total TVA Collectée (Brute)", f"{data['tva_collectee']:.2f} €", self.accent_color),
            ("TVA Récupérable (Déductible)", f"{data['tva_deductible']:.2f} €", ft.colors.GREEN_400)
        ]:
            card = ft.Container(
                expand=1,
                bgcolor="#242426",
                border_radius=10,
                border=ft.border.all(1, "#3A3A3E"),
                padding=15,
                content=ft.Column(
                    controls=[
                        ft.Text(title, size=12, color="#A0A0A5", text_align=ft.TextAlign.CENTER),
                        ft.Text(val, size=22, weight=ft.FontWeight.BOLD, color=color, text_align=ft.TextAlign.CENTER)
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    alignment=ft.MainAxisAlignment.CENTER
                )
            )
            cards.append(card)
        
        cards_row = ft.Row(controls=cards, spacing=15, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        solde_positif = data['solde_tva'] >= 0
        bg_solde = "#1C2826" if solde_positif else "#2D1A1A"
        color_solde = ft.colors.GREEN_400 if solde_positif else ft.colors.RED_400
        txt_solde = f"TVA À REVERSER : {data['solde_tva']:.2f} €" if solde_positif else f"CRÉDIT DE TVA À REPORTER : {abs(data['solde_tva']):.2f} €"

        solde_frame = ft.Container(
            bgcolor=bg_solde,
            border_radius=10,
            padding=15,
            alignment=ft.alignment.center,
            content=ft.Text(f"État du solde estimé : {txt_solde}", size=15, weight=ft.FontWeight.BOLD, color=color_solde)
        )

        detail_controls = [
            ft.Text("📌 Détails analytiques des ventilations", size=14, weight=ft.FontWeight.BOLD),
            ft.Divider(height=10, color="transparent")
        ]
        
        details_list = [
            ("TVA Collectée standard - Taux Normal (20%)", f"{data['tva_20']:.2f} €"),
            ("TVA Collectée intermédiaire - Taux Réduit (10%)", f"{data['tva_10']:.2f} €"),
            ("TVA Collectée première nécessité - Taux Réduit (5.5%)", f"{data['tva_5']:.2f} €"),
            ("TVA issue des opérations d'Auto-liquidation Intracommunautaires", f"{data['tva_autoliquidee']:.2f} €"),
            ("Volume des charges supportées hors taxes (HT)", f"{data['total_charges_ht']:.2f} €")
        ]

        for libelle, val in details_list:
            detail_controls.append(
                ft.Row(
                    controls=[
                        ft.Text(libelle, size=13, color="#CCCCCC"),
                        ft.Text(val, size=13, weight=ft.FontWeight.BOLD)
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                )
            )

        detail_box = ft.Container(
            bgcolor="#141416",
            border_radius=10,
            padding=15,
            expand=True,
            content=ft.Column(controls=detail_controls, scroll=ft.ScrollMode.AUTO, spacing=10)
        )

        self.main_container.content = ft.Column(
            controls=[
                cards_row,
                solde_frame,
                detail_box
            ],
            expand=True,
            spacing=15
        )

    def _afficher_registre_charges(self):
        """Rend l'onglet registre splité en 2 (Formulaire à gauche (40%), Liste scrollable à droite (60%))."""
        e_desc = ft.TextField(label="Désignation de la dépense", hint_text="ex: Abonnement Serveur")
        e_ht = ft.TextField(label="Montant Total HT (€)", hint_text="0.00")
        
        combo_taux = ft.Dropdown(
            label="Taux de TVA applicable",
            value="20",
            options=[
                ft.dropdown.Option("20"),
                ft.dropdown.Option("10"),
                ft.dropdown.Option("5.5"),
                ft.dropdown.Option("2.1")
            ]
        )
        
        e_coef = ft.TextField(label="Quotité/Coeff. Récupération (%)", value="100")
        var_auto = ft.Checkbox(label="Opération Auto-liquidée (Intracomm.)", value=False)

        def ajouter_charge(e):
            try:
                desc = e_desc.value.strip() if e_desc.value else ""
                ht = safe_float(e_ht.value)
                taux = safe_float(combo_taux.value)
                coef = safe_float(e_coef.value) if e_coef.value else 100.0
                if not desc or ht <= 0:
                    raise ValueError()
                
                self.app.charges.append({
                    "date": datetime.now().strftime("%d/%m/%Y"),
                    "description": desc,
                    "ht": ht,
                    "taux": taux,
                    "coef_recup": coef,
                    "autoliquide": var_auto.value
                })
                if hasattr(self.app, "save_data"):
                    self.app.save_data()
                
                self.show_snack("Charge enregistrée avec succès. ✔")
                self._afficher_registre_charges()
            except Exception:
                self.show_snack("Erreur : Saisie incorrecte ou manquante.", is_error=True)

        btn_save = ft.ElevatedButton(
            text="💾 Enregistrer la charge",
            bgcolor=ft.colors.GREEN_700,
            color=ft.colors.WHITE,
            height=45,
            on_click=ajouter_charge,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
        )

        form_box = ft.Container(
            expand=4,
            bgcolor="#141416",
            border_radius=10,
            padding=15,
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Text("➕ Nouvelle Charge", size=15, weight=ft.FontWeight.BOLD),
                        alignment=ft.alignment.center
                    ),
                    e_desc,
                    e_ht,
                    combo_taux,
                    e_coef,
                    var_auto,
                    ft.Divider(height=10, color="transparent"),
                    btn_save
                ],
                spacing=12,
                scroll=ft.ScrollMode.AUTO
            )
        )

        list_controls = []
        if not getattr(self.app, "charges", []):
            list_controls.append(
                ft.Container(
                    alignment=ft.alignment.center,
                    padding=40,
                    content=ft.Text("Aucune charge enregistrée.", color="#636366")
                )
            )
        else:
            for c in reversed(self.app.charges):
                try:
                    c_ht = safe_float(c.get("ht", 0))
                    c_taux = safe_float(c.get("taux", 20))
                    c_coef = safe_float(c.get("coef_recup", 100)) / 100.0
                    tva_recup = (c_ht * (c_taux / 100.0)) * c_coef
                    c_desc = c.get("description", "Sans nom")
                    c_date = c.get("date", datetime.now().strftime("%d/%m/%Y"))
                except Exception:
                    c_ht, c_taux, tva_recup, c_desc, c_date = 0.0, 20.0, 0.0, "Donnée corrompue", "--/--/----"

                txt_l = f"📅 {c_date} - {c_desc}\nBase HT: {c_ht:.2f} € | Taux: {c_taux}%"
                
                card = ft.Container(
                    bgcolor="#242426",
                    border_radius=8,
                    padding=12,
                    content=ft.Row(
                        controls=[
                            ft.Text(txt_l, size=13, expand=True),
                            ft.Text(f"TVA Récup.\n{tva_recup:.2f} €", size=13, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_400, text_align=ft.TextAlign.RIGHT)
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                    )
                )
                list_controls.append(card)

        scroll_list = ft.Container(
            expand=6,
            bgcolor="#141416",
            border_radius=10,
            padding=15,
            content=ft.Column(controls=list_controls, scroll=ft.ScrollMode.AUTO, spacing=8)
        )

        self.main_container.content = ft.Row(
            controls=[form_box, scroll_list],
            spacing=15,
            expand=True
        )

    def _afficher_assistant_ca3(self):
        """Génère l'état préparatoire de la liasse Cerfa CA3."""
        data = self._calculer_metriques_financieres()
        
        ca3_lines = [
            ("Ligne 01 : Ventes, Prestations réalisées (Base HT)", f"{data['ca_ht']:.2f} €"),
            ("Ligne 02 : Autres opérations imposables (Auto-liquidation)", f"{data['tva_autoliquidee']:.2f} €"),
            ("Ligne 08 : Opérations au Taux Normal de 20%", f"{data['tva_20']:.2f} €"),
            ("Ligne 09 : Opérations au Taux Réduit de 10%", f"{data['tva_10']:.2f} €"),
            ("Ligne 19 : TVA brute totale due (Collectée)", f"{data['tva_collectee']:.2f} €"),
            ("Ligne 20 : TVA déductible sur biens et services", f"{data['tva_deductible']:.2f} €"),
        ]

        rows = []
        for code, mnt in ca3_lines:
            row_item = ft.Container(
                bgcolor="#1E1E20",
                padding=12,
                border_radius=8,
                content=ft.Row(
                    controls=[
                        ft.Text(code, size=13),
                        ft.Text(mnt, size=14, weight=ft.FontWeight.BOLD, color="#F5A623", font_family="Courier New")
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                )
            )
            rows.append(row_item)

        self.main_container.content = ft.Container(
            bgcolor="#141416",
            border_radius=10,
            padding=15,
            expand=True,
            content=ft.Column(controls=rows, scroll=ft.ScrollMode.AUTO, spacing=8)
        )

    def show_snack(self, message, is_error=False):
        """Notification Snack-bar Flet moderne et non bloquante."""
        page_target = self.page if self.page else (self.app.page if hasattr(self.app, "page") else None)
        if page_target:
            page_target.snack_bar = ft.SnackBar(
                content=ft.Text(message, color=ft.colors.WHITE),
                bgcolor=ft.colors.RED_700 if is_error else ft.colors.GREEN_700,
                dismiss_direction=ft.DismissDirection.HORIZONTAL
            )
            page_target.snack_bar.open = True
            page_target.update()