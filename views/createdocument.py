import flet as ft
from datetime import datetime

CARD_COLOR = "#1E1E22"
PRIMARY_COLOR = "#2B719E"
BG_COLOR = "#1A1A1C"

class CreateDocumentView(ft.Container):
    def __init__(self, app, doc_type="devis", doc_to_edit=None):
        super().__init__()
        self.app = app
        self.doc_type = doc_type
        self.doc_to_edit = doc_to_edit
        self.expand = True
        self.padding = 20
        
        # Initialisation des données
        self.lines = doc_to_edit.get("lignes", []) if doc_to_edit else []
        self.client = doc_to_edit.get("client", "") if doc_to_edit else ""
        
        self._build_interface()

    def did_mount(self):
        self.update_totals()

    def _build_interface(self):
        # --- EN-TÊTE ---
        self.tf_client = ft.Dropdown(
            label="Client / Tiers",
            options=[ft.dropdown.Option(c.get("nom", "Inconnu")) for c in getattr(self.app, "clients", [])],
            value=self.client,
            bgcolor="#242426"
        )
        
        self.btn_pdf = ft.ElevatedButton(
            f"📄 Générer le PDF ({self.doc_type.upper()})", 
            icon=ft.icons.PICTURE_AS_PDF,
            bgcolor=PRIMARY_COLOR, 
            color="white",
            on_click=self.generer_pdf
        )

        # --- TABLEAU DES LIGNES ---
        self.table_lines = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Désignation")),
                ft.DataColumn(ft.Text("Qté")),
                ft.DataColumn(ft.Text("Prix HT")),
                ft.DataColumn(ft.Text("Actions")),
            ],
            rows=[]
        )
        
        # --- RÉSUMÉ ---
        self.lbl_total = ft.Text("Total TTC : 0.00 €", size=20, weight=ft.FontWeight.BOLD)

        self.content = ft.Column([
            ft.Text(f"Création de : {self.doc_type.upper()}", size=24, weight=ft.FontWeight.BOLD),
            ft.Row([self.tf_client, self.btn_pdf]),
            ft.Divider(),
            ft.Container(content=self.table_lines, bgcolor=CARD_COLOR, border_radius=10, padding=10),
            self.lbl_total
        ], scroll=ft.ScrollMode.AUTO)

    def update_totals(self):
        """Met à jour l'affichage de la table et des totaux"""
        self.table_lines.rows.clear()
        total_ttc = 0.0
        
        for idx, line in enumerate(self.lines):
            # Calculs simples
            prix = float(line.get("prix", 0))
            qte = int(line.get("qte", 1))
            total_ligne = prix * qte
            total_ttc += total_ligne
            
            self.table_lines.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(line.get("designation", ""))),
                    ft.DataCell(ft.Text(str(qte))),
                    ft.DataCell(ft.Text(f"{prix:.2f} €")),
                    ft.DataCell(ft.IconButton(ft.icons.DELETE, on_click=lambda e, i=idx: self.supprimer_ligne(i)))
                ])
            )
            
        self.lbl_total.value = f"Total TTC : {total_ttc:.2f} €"
        self.update()

    def supprimer_ligne(self, idx):
        self.lines.pop(idx)
        self.update_totals()

    def generer_pdf(self, e):
        """
        Ici, tu appelles ta logique de génération PDF existante.
        Flet sert à créer l'interface, la bibliothèque (ex: ReportLab) 
        reste indépendante et fonctionnera toujours.
        """
        self.app.page.show_snack_bar(ft.SnackBar(content=ft.Text("Génération du PDF lancée... 🚀")))
        # Exemple : self.app.generator.create_pdf(self.lines, ...)
        print("Lancement de la génération PDF...")