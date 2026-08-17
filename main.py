import flet as ft
import json
from pathlib import Path
from datetime import datetime
from views.create_document import CreateDocumentView

# ============================================================
# OUTILS
# ============================================================

def sanitize_for_json(obj):
    """Convertit les objets non sérialisables en JSON."""
    if isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [sanitize_for_json(i) for i in obj]
    if isinstance(obj, (Path, datetime)):
        return str(obj)
    return obj


# ============================================================
# APPLICATION PRINCIPALE
# ============================================================

class FacturationAndroidApp:

    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Gestion Auto Entreprise par Francky"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.padding = 0
        self.page.window_min_width = 900
        self.page.window_min_height = 600
        
        self.page.scroll = None

        # Dossier des données
        self.data_dir = Path(__file__).parent / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.database = self.data_dir / "database.json"

        # États et Données globales
        self.devis = []
        self.factures = []
        self.clients = []
        self.articles = []
        self.fournisseurs = []
        self.mails = []
        self.bons_commande = []
        self.bons_livraison = []
        self.agenda = {}

        self.entreprise = {
            "nom": "MA GESTION",
            "statut_juridique": "Micro-Entreprise",
            "adresse": "",
            "telephone": "",
            "email": "",
            "site": "",
            "siret": "",
            "tva_activee": False,
            "accent_color": "#2B719E",
        }

        self.load_data()

        self.content_area = ft.Container(
            expand=True,
            padding=20,
        )

        self.setup_layout()
        self.navigate_to("Dashboard")

    def load_data(self):
        """Charge les données du fichier JSON."""
        if not self.database.exists():
            self.save_data()
            return
        try:
            with open(self.database, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.devis = data.get("devis", [])
            self.factures = data.get("factures", [])
            self.clients = data.get("clients", [])
            self.articles = data.get("articles", [])
            self.fournisseurs = data.get("fournisseurs", [])
            self.mails = data.get("mails", [])
            self.bons_commande = data.get("bons_commande", [])
            self.bons_livraison = data.get("bons_livraison", [])
            self.agenda = data.get("agenda", {})

            entreprise = data.get("entreprise")
            if isinstance(entreprise, dict):
                self.entreprise.update(entreprise)
            print("Base de données chargée avec succès.")
        except Exception as e:
            print("Erreur lors du chargement :", e)

    def save_data(self):
        """Sauvegarde les données au format JSON."""
        package = {
            "devis": self.devis,
            "factures": self.factures,
            "clients": self.clients,
            "articles": self.articles,
            "fournisseurs": self.fournisseurs,
            "mails": self.mails,
            "bons_commande": self.bons_commande,
            "bons_livraison": self.bons_livraison,
            "agenda": self.agenda,
            "entreprise": self.entreprise,
        }
        try:
            with open(self.database, "w", encoding="utf-8") as f:
                json.dump(sanitize_for_json(package), f, indent=4, ensure_ascii=False)
            print("Base de données sauvegardée.")
        except Exception as e:
            print("Erreur lors de la sauvegarde :", e)

    def setup_layout(self):
        """Prépare et monte l'architecture graphique principale (Sidebar + Content)."""
        self.sidebar_titre = ft.Text(
            self.entreprise.get("nom", "GESTION"),
            size=22,
            weight=ft.FontWeight.BOLD,
            text_align=ft.TextAlign.CENTER,
        )

        titre_container = ft.Container(
            content=self.sidebar_titre,
            padding=20,
        )

        self.menu_column = ft.Column(
            spacing=8,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

        btn_reglages = ft.OutlinedButton(
            "⚙️ Réglages",
            width=220,
            height=45,
            on_click=lambda e: self.navigate_to("Réglages")
        )

        self.sidebar = ft.Container(
            width=250,
            bgcolor="#1A1A1C",
            padding=10,
            content=ft.Column(
                controls=[
                    titre_container,
                    ft.Divider(),
                    self.menu_column,
                    ft.Divider(),
                    btn_reglages,
                ],
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            ),
        )

        self.page.add(
            ft.Row(
                controls=[
                    self.sidebar,
                    self.content_area,
                ],
                expand=True,
                spacing=0,
            )
        )

        self.refresh_sidebar()

    def refresh_sidebar(self):
        """Reconstruit dynamiquement la liste des onglets selon la configuration de la TVA."""
        accent = self.entreprise.get("accent_color", "#2B719E")
        self.sidebar_titre.value = self.entreprise.get("nom", "GESTION").upper()

        menu = [
            ("📊 Dashboard", "Dashboard"),
            ("🧾 Facturation", "Facturation"),
            ("📦 Articles", "Articles"),
            ("👥 Clients", "Clients"),
            ("🚚 Fournisseurs", "Fournisseurs"),
            ("📚 Visionneuse PDF", "PDFViewer"),
            ("📈 Finance", "Finance"),
        ]

        if self.entreprise.get("tva_activee", False):
            menu.append(("🧮 Comptabilité", "Comptabilite"))

        menu.extend([
            ("✉️ Mails", "Mails"),
            ("📅 Agenda", "Agenda"),
            ("🏢 Entreprise", "Entreprise"),
        ])

        self.menu_buttons = []
        for texte, vue in menu:
            btn = ft.ElevatedButton(
                texte,
                width=220,
                height=45,
                bgcolor=accent,
                color="white",
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                on_click=lambda e, v=vue: self.navigate_to(v)
            )
            self.menu_buttons.append(btn)

        self.menu_column.controls = self.menu_buttons
        
        try:
            self.menu_column.update()
        except Exception:
            pass

    def navigate_to(self, view_name, **kwargs):
        """Gère le routage et le chargement paresseux des différentes vues."""
        print(f"Tentative de navigation vers : {view_name}")
        
        self.refresh_sidebar()
        self.content_area.content = None

        try:
            if view_name == "Dashboard":
                from views.dashboard import DashboardView
                self.content_area.content = DashboardView(self)
            elif view_name == "Facturation":
                from views.facturation import FacturationView
                self.content_area.content = FacturationView(self)
            elif view_name == "Articles":
                from views.articles import ArticlesView
                self.content_area.content = ArticlesView(self)
            elif view_name == "Clients":
                from views.clients import ClientsView
                self.content_area.content = ClientsView(self)
            elif view_name == "Fournisseurs":
                from views.fournisseurs import FournisseursView
                self.content_area.content = FournisseursView(self)
            elif view_name == "Finance":
                from views.finance import FinanceView
                self.content_area.content = FinanceView(self)
            elif view_name == "Comptabilite":
                from views.comptabilite import ComptabiliteView
                self.content_area.content = ComptabiliteView(self)
            elif view_name == "Agenda":
                from views.agenda import AgendaView
                self.content_area.content = AgendaView(self)
            elif view_name == "Entreprise":
                from views.entreprise import EntrepriseView
                self.content_area.content = EntrepriseView(self)
            elif view_name == "Mails":
                from views.mails import MailsView
                self.content_area.content = MailsView(self)
            elif view_name == "PDFViewer":
                from views.pdfviewer import PDFViewer
                self.content_area.content = PDFViewer(self, **kwargs)
            elif view_name == "Réglages":
                from views.reglages import ReglagesView
                self.content_area.content = ReglagesView(self)

            elif view_name == "create_document":
                doc_type = kwargs.get("doc_type", "devis")
                doc_to_edit = kwargs.get("doc_to_edit", None)
                self.content_area.content = CreateDocumentView(self, doc_type=doc_type, doc_to_edit=doc_to_edit)

            elif view_name == "NouveauDevis":
                self.content_area.content = CreateDocumentView(self, doc_type="devis")
            elif view_name == "NouvelleFacture":
                self.content_area.content = CreateDocumentView(self, doc_type="facture")
            elif view_name == "NouveauBonCommande":
                self.content_area.content = CreateDocumentView(self, doc_type="bon_commande")
            elif view_name == "NouveauBonLivraison":
                self.content_area.content = CreateDocumentView(self, doc_type="bon_livraison")
            elif view_name == "ModifierDocument":
                self.content_area.content = CreateDocumentView(
                    self, 
                    doc_type=kwargs.get("doc_type", "devis"), 
                    doc_to_edit=kwargs.get("doc_to_edit", None)
                )

            else:
                self.content_area.content = ft.Container(
                    expand=True,
                    alignment=ft.Alignment(0, 0),
                    content=ft.Column(
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon("warning_amber_rounded", size=80, color="orange"),
                            ft.Text(f"Vue '{view_name}' introuvable.", size=24, weight=ft.FontWeight.BOLD),
                        ],
                    ),
                )
        except Exception as e:
            self.content_area.content = ft.Container(
                expand=True,
                alignment=ft.Alignment(0, 0),
                content=ft.Column(
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon("error_outline", color="red", size=80),
                        ft.Text("Erreur lors du chargement de la vue", size=22, weight=ft.FontWeight.BOLD),
                        ft.Text(str(e), selectable=True, color="red"),
                    ],
                ),
            )
        
        self.page.update()

def main(page: ft.Page):
    FacturationAndroidApp(page)

if __name__ == "__main__":
    ft.app(target=main)
