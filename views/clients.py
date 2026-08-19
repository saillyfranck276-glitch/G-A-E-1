# views/membres.py
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import flet as ft

IS_ANDROID = "ANDROID_STORAGE" in os.environ or "ANDROID_ROOT" in os.environ or hasattr(sys, "getandroidapilevel")


class MembresView(ft.Container):
    def __init__(self, app):
        super().__init__(expand=True)
        self.app = app
        self.accent_color = getattr(self.app, "association", {}).get("accent_color", "#1E3A8A")
        
        self.current_editing_index = None

        # --- INITIALISATION DU FILEPICKER (PHOTO) ---
        self.file_picker = ft.FilePicker(on_result=self.on_photo_picked)

        # --- COMPOSANTS DU FORMULAIRE ---
        self.input_nom = ft.TextField(label="Nom", expand=True)
        self.input_prenom = ft.TextField(label="Prénom", expand=True)
        self.dropdown_sexe = ft.Dropdown(
            label="Sexe",
            expand=True,
            options=[
                ft.dropdown.Option("H", "Homme"),
                ft.dropdown.Option("F", "Femme"),
            ]
        )
        self.input_date_naissance = ft.TextField(label="Né(e) le (JJ/MM/AAAA)", expand=True, hint_text="Ex: 14/02/2010")
        self.input_photo = ft.TextField(label="Photo", expand=True, read_only=True, hint_text="Aucune photo sélectionnée")
        
        self.input_email = ft.TextField(label="Adresse Email", expand=True, keyboard_type=ft.KeyboardType.EMAIL)
        self.input_telephone = ft.TextField(label="N° Téléphone", expand=True, keyboard_type=ft.KeyboardType.PHONE)
        
        self.input_rue = ft.TextField(label="Rue / Avenue / Boulevard", expand=True)
        self.input_cp = ft.TextField(label="Code Postal", expand=True, keyboard_type=ft.KeyboardType.NUMBER)
        self.input_ville = ft.TextField(label="Ville", expand=True)
        
        self.input_responsable = ft.TextField(label="Responsable Légal (Si mineur)", expand=True, hint_text="Nom, Prénom + Lien (Ex: Père)")
        self.check_medical = ft.Checkbox(label="Certificat Médical OK / Fourni", value=False)
        self.check_accord_soins = ft.Checkbox(label="Accord parental soins urgences", value=False)
        self.input_allergies = ft.TextField(label="Allergies / Contre-indications", expand=True, hint_text="Ex: Asthme... (Laisser vide si RAS)")
        self.input_fiche_medecin = ft.TextField(label="Notes du médecin / Suivi", multiline=True, min_lines=2, max_lines=4, expand=True)

        self.input_licence = ft.TextField(label="N° Licence FFK", expand=True)
        self.check_licence_prise_ffk = ft.Checkbox(label="Licence prise sur FFK", value=False)
        self.dropdown_grade = ft.Dropdown(
            label="Grade Actuel",
            expand=True,
            options=[
                ft.dropdown.Option("Blanche (6ème Kyu)"),
                ft.dropdown.Option("Jaune (5ème Kyu)"),
                ft.dropdown.Option("Orange (4ème Kyu)"),
                ft.dropdown.Option("Verte (3ème Kyu)"),
                ft.dropdown.Option("Bleue (2ème Kyu)"),
                ft.dropdown.Option("Marron (1er Kyu)"),
                ft.dropdown.Option("Noire 1er Dan"),
                ft.dropdown.Option("Noire 2ème Dan"),
                ft.dropdown.Option("Noire 3ème Dan ou +"),
            ]
        )
        self.input_historique_licences = ft.TextField(
            label="Historique des saisons passées", 
            multiline=True, 
            min_lines=2, 
            max_lines=4, 
            expand=True,
            hint_text="Ex: 2023/2024: Club de Lyon..."
        )

        # --- COMPOSANTS DE L'ÉCRAN LISTE ---
        self.input_recherche = ft.TextField(
            label="Rechercher un adhérent...",
            prefix_icon=ft.icons.SEARCH,
            expand=True,
            on_change=self.filtrer_membres
        )

        self.dropdown_filtre_cotis = ft.Dropdown(
            label="Filtrer par Cotisation",
            expand=True,
            options=[
                ft.dropdown.Option("Tous", "Toutes les cotisations"),
                ft.dropdown.Option("Soldes", "Soldés uniquement"),
                ft.dropdown.Option("RestantDu", "Restant dû uniquement"),
            ],
            value="Tous",
            on_change=self.filtrer_membres
        )

        # Bouton Imprimer principal qui redirige vers PdfViewerView
        self.btn_export_pdf = ft.ElevatedButton(
            "📄 Imprimer / PDF",
            icon=ft.icons.PICTURE_AS_PDF,
            bgcolor="#334155",
            color=ft.colors.WHITE,
            height=44,
            on_click=self.rediriger_vers_pdfviewer
        )
        
        self.table_membres = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Adhérent")),
                ft.DataColumn(ft.Text("Licence / Grade")),
                ft.DataColumn(ft.Text("Contact")),
                ft.DataColumn(ft.Text("Santé / FFK")),
                ft.DataColumn(ft.Text("Cotisation / Solde")),
                ft.DataColumn(ft.Text("Actions")),
            ],
            rows=[]
        )

        self.view_container = ft.Container(expand=True)
        self.content = ft.Column([self.view_container], expand=True)

        self.afficher_ecran_liste()

    def did_mount(self):
        page_obj = self.page or getattr(self.app, "page", None)
        if page_obj:
            if self.file_picker not in page_obj.overlay:
                page_obj.overlay.append(self.file_picker)
            page_obj.update()

    def rediriger_vers_pdfviewer(self, e, membre=None):
        target_membre = membre
        if not target_membre and getattr(self.app, "membres", []):
            target_membre = self.app.membres[0]

        self.app.membre_selectionne = target_membre

        from views.pdfviewer import PdfViewerView

        # 1. Méthodes standard sur la classe App
        if hasattr(self.app, "changer_vue"):
            self.app.changer_vue("pdfviewer", membre=target_membre)
        elif hasattr(self.app, "afficher_vue"):
            self.app.afficher_vue(PdfViewerView(self.app, membre=target_membre))
        elif hasattr(self.app, "changer_ecran"):
            self.app.changer_ecran(PdfViewerView(self.app, membre=target_membre))
        elif hasattr(self.app, "navigate"):
            self.app.navigate("pdfviewer")
        # 2. Remplacement direct des conteneurs de contenu fréquents
        elif hasattr(self.app, "content_area") and self.app.content_area:
            self.app.content_area.content = PdfViewerView(self.app, membre=target_membre)
            self.app.content_area.update()
        elif hasattr(self.app, "main_content") and self.app.main_content:
            self.app.main_content.content = PdfViewerView(self.app, membre=target_membre)
            self.app.main_content.update()
        elif hasattr(self.app, "body_container") and self.app.body_container:
            self.app.body_container.content = PdfViewerView(self.app, membre=target_membre)
            self.app.body_container.update()
        # 3. Navigation par route Flet
        elif self.page:
            try:
                self.page.go("/pdfviewer")
            except Exception:
                pass

    # ============================================================
    # 🧮 LOGIQUE COMPTABLE & FINANCIÈRE INDIVIDUELLE
    # ============================================================

    def calculer_age(self, date_str):
        if not date_str:
            return None
        formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]
        for fmt in formats:
            try:
                birth = datetime.strptime(str(date_str).strip(), fmt)
                today = datetime.today()
                return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
            except ValueError:
                continue
        return None

    def obtenir_tarif_theorique(self, membre):
        tarifs = getattr(self.app, "association", {}).get("tarifs", {"u12": 100.0, "u18": 130.0, "adult": 160.0})
        age = self.calculer_age(membre.get("date_naissance"))
        if age is None:
            return float(tarifs.get("adult", 160.0))
        if age < 12:
            return float(tarifs.get("u12", 100.0))
        elif age < 18:
            return float(tarifs.get("u18", 130.0))
        else:
            return float(tarifs.get("adult", 160.0))

    def obtenir_reglements_membre(self, nom_membre, prenom_membre):
        nom_cle = f"{str(nom_membre).strip()} {str(prenom_membre).strip()}".upper()
        reglements = []
        total_paye = 0.0

        cotis_list = getattr(self.app, "cotisations", [])
        for c in cotis_list:
            membre_cotis = str(c.get("membre", "")).strip().upper()
            if membre_cotis == nom_cle:
                reglements.append(c)
                if c.get("statut") == "Encaissé / Validé":
                    try:
                        total_paye += float(c.get("montant", 0))
                    except ValueError:
                        pass
        return reglements, total_paye

    def obtenir_bilan_financier_membre(self, membre):
        tarif_du = self.obtenir_tarif_theorique(membre)
        _, total_paye = self.obtenir_reglements_membre(membre.get("nom", ""), membre.get("prenom", ""))
        solde = total_paye - tarif_du

        is_solde = solde >= -0.01
        reste_a_payer = abs(solde) if not is_solde else 0.0

        return {
            "tarif_du": tarif_du,
            "total_paye": total_paye,
            "solde": solde,
            "reste_a_payer": reste_a_payer,
            "is_solde": is_solde,
            "badge_texte": "✅ Soldé" if is_solde else f"🔴 Dû: {reste_a_payer:.2f} €",
            "color": ft.colors.GREEN_400 if is_solde else ft.colors.RED_400
        }

    # ============================================================
    # 🖥️ GESTION DES ÉCRANS
    # ============================================================

    def afficher_ecran_liste(self):
        self.current_editing_index = None
        self.load_membres_table()

        self.view_container.content = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=15,
            controls=[
                ft.Row([
                    ft.Icon(ft.icons.PEOPLE_ROUNDED, size=28, color=self.accent_color),
                    ft.Text("Adhérents & Licenciés", size=20, weight=ft.FontWeight.BOLD),
                ]),
                ft.Divider(),
                
                ft.ResponsiveRow([
                    ft.Container(self.input_recherche, col={"sm": 12, "md": 7, "lg": 8}),
                    ft.Container(self.dropdown_filtre_cotis, col={"sm": 12, "md": 5, "lg": 4}),
                ], run_spacing=10),

                ft.Row([
                    self.btn_export_pdf,
                    ft.OutlinedButton(
                        "🔄 Renouvellement",
                        icon=ft.icons.AUTORENEW,
                        height=44,
                        on_click=self.ouvrir_dialogue_renouvellement
                    ),
                    ft.ElevatedButton(
                        "Ajouter",
                        icon=ft.icons.PERSON_ADD,
                        bgcolor=self.accent_color,
                        color=ft.colors.WHITE,
                        height=44,
                        on_click=lambda e: self.afficher_ecran_formulaire()
                    )
                ], spacing=10, wrap=True),
                
                ft.Container(
                    bgcolor="#1F2937",
                    padding=10,
                    border_radius=10,
                    content=ft.Column(
                        scroll=ft.ScrollMode.AUTO,
                        controls=[
                            ft.Row(
                                scroll=ft.ScrollMode.AUTO,
                                controls=[self.table_membres]
                            )
                        ]
                    )
                )
            ]
        )
        if self.page:
            self.update()

    def afficher_ecran_formulaire(self, index_membre=None):
        self.current_editing_index = index_membre
        titre_form = "Créer une fiche adhérent"
        icon_form = ft.icons.PERSON_ADD_ROUNDED
        
        if index_membre is not None:
            titre_form = "Modifier l'adhérent"
            icon_form = ft.icons.EDIT_NOTE_ROUNDED
            self.pre_remplir_formulaire(index_membre)
        else:
            self.vider_formulaire()

        self.view_container.content = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=20,
            controls=[
                ft.Row([
                    ft.Icon(icon_form, size=28, color=self.accent_color),
                    ft.Text(titre_form, size=18, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    ft.OutlinedButton("Retour", icon=ft.icons.ARROW_BACK, on_click=lambda e: self.afficher_ecran_liste())
                ]),
                ft.Divider(),

                self.creer_section_card("1. Identité & Photo", [
                    ft.ResponsiveRow([
                        ft.Container(self.input_nom, col={"sm": 12, "md": 6}),
                        ft.Container(self.input_prenom, col={"sm": 12, "md": 6}),
                    ]),
                    ft.ResponsiveRow([
                        ft.Container(self.dropdown_sexe, col={"sm": 12, "md": 4}),
                        ft.Container(self.input_date_naissance, col={"sm": 12, "md": 8}),
                    ]),
                    ft.Row([
                        self.input_photo,
                        ft.IconButton(
                            icon=ft.icons.ADD_A_PHOTO, 
                            icon_color=self.accent_color, 
                            tooltip="Sélectionner une photo",
                            on_click=lambda e: self.file_picker.pick_files(file_type=ft.FilePickerFileType.IMAGE)
                        )
                    ], spacing=10)
                ]),

                self.creer_section_card("2. Contacts & Adresse", [
                    ft.ResponsiveRow([
                        ft.Container(self.input_telephone, col={"sm": 12, "md": 6}),
                        ft.Container(self.input_email, col={"sm": 12, "md": 6}),
                    ]),
                    ft.Row([self.input_rue]),
                    ft.ResponsiveRow([
                        ft.Container(self.input_cp, col={"sm": 12, "md": 4}),
                        ft.Container(self.input_ville, col={"sm": 12, "md": 8}),
                    ]),
                ]),

                self.creer_section_card("3. Santé & Responsabilité", [
                    ft.Row([self.input_responsable]),
                    ft.ResponsiveRow([
                        ft.Container(self.check_medical, col={"sm": 12, "md": 6}),
                        ft.Container(self.check_accord_soins, col={"sm": 12, "md": 6}),
                    ]),
                    ft.Row([self.input_allergies]),
                    ft.Row([self.input_fiche_medecin]),
                ]),

                self.creer_section_card("4. Licence & Sportif", [
                    ft.ResponsiveRow([
                        ft.Container(self.input_licence, col={"sm": 12, "md": 6}),
                        ft.Container(self.dropdown_grade, col={"sm": 12, "md": 6}),
                    ]),
                    ft.Row([self.check_licence_prise_ffk]),
                    ft.Row([self.input_historique_licences]),
                ]),

                ft.Row([
                    ft.TextButton("Annuler", icon=ft.icons.CANCEL, icon_color=ft.colors.RED_400, on_click=lambda e: self.afficher_ecran_liste()),
                    ft.ElevatedButton(
                        "Enregistrer", 
                        icon=ft.icons.SAVE, 
                        bgcolor=ft.colors.GREEN_700, 
                        color=ft.colors.WHITE, 
                        height=48,
                        on_click=self.sauvegarder_fiche
                    )
                ], alignment=ft.MainAxisAlignment.END, spacing=10),
                ft.Container(height=20)
            ]
        )
        if self.page:
            self.update()

    def creer_section_card(self, titre, composants):
        return ft.Container(
            bgcolor="#1F2937",
            padding=15,
            border_radius=10,
            content=ft.Column([
                ft.Text(titre, size=14, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_200),
                ft.Divider(color=ft.colors.GREY_800, height=8),
                ft.Column(controls=composants, spacing=10)
            ], spacing=5)
        )

    # ============================================================
    # 🔄 MODULE DE RENOUVELLEMENT DE LICENCE
    # ============================================================

    def ouvrir_dialogue_renouvellement(self, e):
        page_obj = self.page or getattr(self.app, "page", None)
        if not page_obj:
            return

        saison_actuelle = str(getattr(self.app, "saison_active", "2024-2025"))

        saisons_disponibles = []
        if hasattr(self.app, "db") and self.app.db:
            if hasattr(self.app.db, "lister_saisons"):
                toutes_saisons = self.app.db.lister_saisons()
                saisons_disponibles = [str(s) for s in toutes_saisons if str(s) != saison_actuelle]

        if not saisons_disponibles:
            try:
                start_year = int(saison_actuelle.split("-")[0])
            except Exception:
                start_year = 2024
            saisons_disponibles = [f"{start_year - i}-{start_year - i + 1}" for i in range(1, 6)]

        noms_existants = [
            f"{m.get('nom', '').strip().upper()} {m.get('prenom', '').strip().lower()}" 
            for m in self.app.membres
        ]

        membres_trouves_global = {}
        for s in reversed(saisons_disponibles):
            anciens = []
            if hasattr(self.app, "db") and self.app.db:
                if hasattr(self.app.db, "charger_adherents_par_saison"):
                    anciens = self.app.db.charger_adherents_par_saison(s)
                else:
                    res = self.app.db.charger_tous_les_adherents(s)
                    if isinstance(res, tuple) and len(res) > 0:
                        anciens = res[0]

            if anciens:
                for m in anciens:
                    cle = f"{m.get('nom', '').strip().upper()} {m.get('prenom', '').strip().lower()}"
                    if cle not in noms_existants:
                        membres_trouves_global[cle] = (m, s)

        options_membres = [ft.dropdown.Option("tous", "-- Tous les membres inscriptibles --")]
        for cle, (m_data, s_source) in membres_trouves_global.items():
            nom_aff = f"{m_data.get('nom', '').upper()} {m_data.get('prenom', '')}"
            options_membres.append(ft.dropdown.Option(cle, f"{nom_aff} (Ex: S{s_source})"))

        dropdown_membres = ft.Dropdown(
            label="Sélectionner un membre",
            expand=True,
            options=options_membres,
            value="tous"
        )

        dropdown_saison = ft.Dropdown(
            label="Saison source",
            expand=True,
            options=[ft.dropdown.Option("toutes", "Toutes les anciennes saisons")] + [
                ft.dropdown.Option(s, f"Saison {s}") for s in saisons_disponibles
            ],
            value="toutes"
        )

        input_recherche_modal = ft.TextField(
            label="Filtrer par nom...",
            prefix_icon=ft.icons.SEARCH,
            expand=True
        )

        container_liste = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
        checkboxes_map = {}

        def actualiser_liste_dialogue(evt=None):
            checkboxes_map.clear()
            container_liste.controls.clear()

            saison_choisie = dropdown_saison.value
            membre_choisi = dropdown_membres.value
            filtre_txt = input_recherche_modal.value.strip().lower() if input_recherche_modal.value else ""

            saisons_a_charger = saisons_disponibles if saison_choisie == "toutes" else [saison_choisie]
            
            liste_controls = []
            for cle, (m_data, s_source) in membres_trouves_global.items():
                if s_source not in saisons_a_charger:
                    continue

                if membre_choisi != "tous" and cle != membre_choisi:
                    continue

                nom_affiche = f"{m_data.get('nom', '').upper()} {m_data.get('prenom', '')}"
                grade = m_data.get('grade_actuel', 'S.G.')
                
                if filtre_txt and filtre_txt not in nom_affiche.lower():
                    continue

                cb = ft.Checkbox(
                    label=f"{nom_affiche} ({grade}) - Ex S{s_source}",
                    value=True
                )
                checkboxes_map[cb] = (m_data, s_source)
                liste_controls.append(cb)

            if not liste_controls:
                container_liste.controls.append(
                    ft.Text("Aucun membre correspondant.", italic=True, color=ft.colors.GREY_400, size=12)
                )
            else:
                container_liste.controls.extend(liste_controls)

            if page_obj:
                page_obj.update()

        dropdown_saison.on_change = actualiser_liste_dialogue
        dropdown_membres.on_change = actualiser_liste_dialogue
        input_recherche_modal.on_change = actualiser_liste_dialogue

        def valider_renouvellement(ev):
            membres_ajoutes = 0
            for cb, (m_data, s_source) in checkboxes_map.items():
                if cb.value:
                    nouvelle_fiche = dict(m_data)
                    nouvelle_fiche["certificat_medical_valide"] = False
                    nouvelle_fiche["licence_prise_ffk"] = False
                    histo = nouvelle_fiche.get("historique_licences", "")
                    nouvelle_fiche["historique_licences"] = f"Renouvelé en {saison_actuelle} (Ex: {s_source})\n{histo}".strip()
                    
                    self.app.membres.append(nouvelle_fiche)
                    membres_ajoutes += 1

            if membres_ajoutes > 0:
                if hasattr(self.app, "save_data"):
                    self.app.save_data()
                self.afficher_ecran_liste()
                msg = f"🎉 {membres_ajoutes} membre(s) réinscrit(s) pour {saison_actuelle} !"
                bg = ft.colors.GREEN_700
            else:
                msg = "Aucun membre sélectionné."
                bg = ft.colors.BLUE_700

            dialog_renouvellement.open = False
            if page_obj:
                page_obj.snack_bar = ft.SnackBar(content=ft.Text(msg), bgcolor=bg)
                page_obj.snack_bar.open = True
                page_obj.update()

        def fermer_dialogue(ev):
            dialog_renouvellement.open = False
            if page_obj:
                page_obj.update()

        dialog_renouvellement = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.icons.AUTORENEW, color=self.accent_color, size=22),
                ft.Text(f"Renouvellement pour {saison_actuelle}", size=16)
            ]),
            content=ft.Container(
                width=380,
                height=420,
                content=ft.Column(
                    controls=[
                        ft.Row([dropdown_membres], spacing=5),
                        ft.Row([dropdown_saison], spacing=5),
                        ft.Row([input_recherche_modal], spacing=5),
                        ft.Divider(height=5),
                        container_liste
                    ],
                    spacing=8
                )
            ),
            actions=[
                ft.TextButton("Annuler", on_click=fermer_dialogue),
                ft.ElevatedButton("Réinscrire", bgcolor=ft.colors.GREEN_700, color=ft.colors.WHITE, on_click=valider_renouvellement)
            ]
        )

        if dialog_renouvellement not in page_obj.overlay:
            page_obj.overlay.append(dialog_renouvellement)

        dialog_renouvellement.open = True
        actualiser_liste_dialogue()

    # ============================================================
    # 🛠️ LOGIQUE DES DONNÉES (CRUD)
    # ============================================================

    def modifier_statut_ffk_direct(self, e, index):
        self.app.membres[index]["licence_prise_ffk"] = e.control.value
        if hasattr(self.app, "save_data"):
            self.app.save_data()

    def load_membres_table(self, filtre_texte="", filtre_cotis="Tous"):
        self.table_membres.rows.clear()
        
        for index, m in enumerate(self.app.membres):
            nom_complet = f"{m.get('nom', '').upper()} {m.get('prenom', '')}"
            
            if filtre_texte and filtre_texte.lower() not in nom_complet.lower():
                continue

            bilan = self.obtenir_bilan_financier_membre(m)

            if filtre_cotis == "Soldes" and not bilan["is_solde"]:
                continue
            elif filtre_cotis == "RestantDu" and bilan["is_solde"]:
                continue

            icon_med = ft.Icon(ft.icons.CHECK_CIRCLE, color=ft.colors.GREEN_400, size=16) if m.get("certificat_medical_valide") else ft.Icon(ft.icons.DANGEROUS, color=ft.colors.RED_400, size=16)
            
            cb_ffk = ft.Checkbox(
                label="FFK",
                value=m.get("licence_prise_ffk", False),
                on_change=lambda e, idx=index: self.modifier_statut_ffk_direct(e, idx)
            )

            statut_sante = ft.Row([
                ft.Text("Certif:"), icon_med,
                ft.Container(content=cb_ffk, padding=ft.padding.only(left=5))
            ], spacing=2, vertical_alignment=ft.CrossAxisAlignment.CENTER)

            widget_cotis = ft.Column([
                ft.Text(bilan["badge_texte"], color=bilan["color"], weight=ft.FontWeight.BOLD, size=11),
                ft.Text(f"Réglé: {bilan['total_paye']:.2f} € / Dû: {bilan['tarif_du']:.2f} €", size=10, color=ft.colors.GREY_400)
            ], spacing=2)

            self.table_membres.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Row([
                            ft.CircleAvatar(
                                foreground_image_url=m.get("photo") if m.get("photo") else None,
                                content=ft.Text(m.get("nom", "X")[0].upper()) if not m.get("photo") else None,
                                radius=14
                            ),
                            ft.Text(nom_complet, weight=ft.FontWeight.BOLD, size=12)
                        ], spacing=8)),
                        ft.DataCell(ft.Text(f"{m.get('grade_actuel', 'Blanche')}\n({m.get('licence_ffk', 'N/A')})", size=11)),
                        ft.DataCell(ft.Text(f"{m.get('telephone', 'N/A')}\n{m.get('email', 'N/A')}", size=11)),
                        ft.DataCell(statut_sante),
                        ft.DataCell(widget_cotis),
                        ft.DataCell(ft.Row([
                            ft.IconButton(
                                icon=ft.icons.VISIBILITY, 
                                icon_color=ft.colors.BLUE_300, 
                                icon_size=20, 
                                tooltip="Voir la liste & détails des règlements", 
                                on_click=lambda e, idx=index: self.ouvrir_boite_details(idx)
                            ),
                            ft.IconButton(
                                icon=ft.icons.PRINT_ROUNDED, 
                                icon_color=ft.colors.PURPLE_300, 
                                icon_size=18, 
                                tooltip="Générer / Imprimer document PDF", 
                                on_click=lambda e, membre_obj=m: self.rediriger_vers_pdfviewer(e, membre_obj)
                            ),
                            ft.IconButton(
                                icon=ft.icons.EDIT, 
                                icon_color=ft.colors.ORANGE_300, 
                                icon_size=18, 
                                tooltip="Modifier l'adhérent", 
                                on_click=lambda e, idx=index: self.afficher_ecran_formulaire(idx)
                            ),
                            ft.IconButton(
                                icon=ft.icons.DELETE_FOREVER_ROUNDED, 
                                icon_color=ft.colors.RED_400, 
                                icon_size=18, 
                                tooltip="Supprimer", 
                                on_click=lambda e, idx=index: self.supprimer_fiche(idx)
                            ),
                        ], spacing=0))
                    ]
                )
            )

    def sauvegarder_fiche(self, e):
        if not self.input_nom.value or not self.input_prenom.value:
            return

        dictionnaire_membre = {
            "nom": self.input_nom.value.strip(),
            "prenom": self.input_prenom.value.strip(),
            "sexe": self.dropdown_sexe.value if self.dropdown_sexe.value else "H",
            "date_naissance": self.input_date_naissance.value,
            "photo": self.input_photo.value,
            "email": self.input_email.value,
            "telephone": self.input_telephone.value,
            "adresse_rue": self.input_rue.value,
            "adresse_cp": self.input_cp.value,
            "adresse_ville": self.input_ville.value,
            "responsable_legal": self.input_responsable.value,
            "certificat_medical_valide": self.check_medical.value,
            "accord_parental_soins": self.check_accord_soins.value,
            "allergies": self.input_allergies.value,
            "fiche_medecin": self.input_fiche_medecin.value,
            "licence_ffk": self.input_licence.value,
            "licence_prise_ffk": self.check_licence_prise_ffk.value,
            "grade_actuel": self.dropdown_grade.value if self.dropdown_grade.value else "Blanche (6ème Kyu)",
            "historique_licences": self.input_historique_licences.value
        }

        if self.current_editing_index is not None:
            self.app.membres[self.current_editing_index] = dictionnaire_membre
        else:
            self.app.membres.append(dictionnaire_membre)

        if hasattr(self.app, "save_data"):
            self.app.save_data()
        self.afficher_ecran_liste()

    def supprimer_fiche(self, index):
        page_obj = self.page or getattr(self.app, "page", None)
        
        def confirmer_suppression(e):
            self.app.membres.pop(index)
            if hasattr(self.app, "save_data"):
                self.app.save_data()
            dialog_confirmation.open = False
            if page_obj:
                page_obj.update()
            self.afficher_ecran_liste()

        dialog_confirmation = ft.AlertDialog(
            title=ft.Text("⚠️ Suppression", size=16),
            content=ft.Text(f"Supprimer la fiche de {self.app.membres[index].get('nom').upper()} {self.app.membres[index].get('prenom')} ?", size=13),
            actions=[
                ft.TextButton("Non", on_click=lambda e: setattr(dialog_confirmation, "open", False) or (self.page or self.app.page).update()),
                ft.ElevatedButton("Oui, supprimer", bgcolor=ft.colors.RED_700, color=ft.colors.WHITE, on_click=confirmer_suppression)
            ]
        )
        if page_obj:
            if dialog_confirmation not in page_obj.overlay:
                page_obj.overlay.append(dialog_confirmation)
            dialog_confirmation.open = True
            page_obj.update()

    # ============================================================
    # 👁️ POPUP RÈGLEMENTS & DETAILS
    # ============================================================

    def ouvrir_boite_details(self, index):
        page_obj = self.page or getattr(self.app, "page", None)
        m = self.app.membres[index]
        adresse = f"{m.get('adresse_rue', '')}\n{m.get('adresse_cp', '')} {m.get('adresse_ville', '')}".strip()
        if not adresse.replace("\n", ""):
            adresse = "Non renseignée"

        sexe_libelle = "Homme" if m.get("sexe") == "H" else ("Femme" if m.get("sexe") == "F" else "N/R")

        bilan = self.obtenir_bilan_financier_membre(m)
        reglements, _ = self.obtenir_reglements_membre(m.get("nom", ""), m.get("prenom", ""))

        liste_widgets_reglements = []
        if not reglements:
            liste_widgets_reglements.append(
                ft.Container(
                    padding=10,
                    content=ft.Text("Aucun règlement enregistré pour cet adhérent.", italic=True, size=11, color=ft.colors.GREY_400)
                )
            )
        else:
            for r in reglements:
                mode = r.get("mode", "Règlement")
                details_mode = []
                if r.get("num_cheque"):
                    details_mode.append(f"Chèque N°{r.get('num_cheque')}")
                if r.get("banque"):
                    details_mode.append(f"Banque: {r.get('banque')}")
                if r.get("num_pass_sport"):
                    details_mode.append(f"Pass'Sport: {r.get('num_pass_sport')}")

                str_details = (" - " + ", ".join(details_mode)) if details_mode else ""
                statut = r.get("statut", "Validé")
                badge_statut_color = ft.colors.GREEN_400 if statut == "Encaissé / Validé" else ft.colors.ORANGE_400

                liste_widgets_reglements.append(
                    ft.Container(
                        padding=10,
                        bgcolor="#111827",
                        border_radius=8,
                        border=ft.border.all(1, "#374151"),
                        content=ft.Column([
                            ft.Row([
                                ft.Row([
                                    ft.Icon(ft.icons.RECEIPT_LONG, size=16, color=ft.colors.BLUE_300),
                                    ft.Text(f"Date : {r.get('date', 'N/A')}", size=12, weight=ft.FontWeight.BOLD),
                                ]),
                                ft.Text(f"{float(r.get('montant', 0)):.2f} €", weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_300, size=13)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            
                            ft.Text(f"Mode : {mode}{str_details}", size=11, color=ft.colors.GREY_300),
                            ft.Row([
                                ft.Text("Statut : ", size=11, color=ft.colors.GREY_400),
                                ft.Text(statut, size=11, weight=ft.FontWeight.BOLD, color=badge_statut_color)
                            ])
                        ], spacing=3)
                    )
                )

        dialog_details = ft.AlertDialog(
            title=ft.Row([
                ft.CircleAvatar(
                    foreground_image_url=m.get("photo") if m.get("photo") else None,
                    content=ft.Text(m.get("nom", "X")[0].upper()) if not m.get("photo") else None,
                    radius=22
                ),
                ft.Column([
                    ft.Text(f"{m.get('nom','').upper()} {m.get('prenom','')}", size=16, weight=ft.FontWeight.BOLD),
                    ft.Text(f"Sexe: {sexe_libelle} | Né(e): {m.get('date_naissance','N/A')}", size=11, color=ft.colors.GREY_400),
                ], spacing=2, expand=True)
            ], spacing=10),
            
            content=ft.Container(
                width=420,
                height=480,
                content=ft.Column(
                    scroll=ft.ScrollMode.AUTO,
                    spacing=12,
                    controls=[
                        ft.Container(
                            padding=12,
                            bgcolor="#1E293B",
                            border_radius=10,
                            content=ft.Column([
                                ft.Row([
                                    ft.Icon(ft.icons.ACCOUNT_BALANCE_WALLET, color=ft.colors.BLUE_300, size=20),
                                    ft.Text("Détail & Historique des Règlements", weight=ft.FontWeight.BOLD, size=14, color=ft.colors.BLUE_200)
                                ]),
                                ft.Divider(height=5, color=ft.colors.GREY_700),
                                ft.Row([
                                    ft.Text("Tarif dû (selon âge) :", size=11, color=ft.colors.GREY_300),
                                    ft.Text(f"{bilan['tarif_du']:.2f} €", size=11, weight=ft.FontWeight.BOLD)
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Row([
                                    ft.Text("Total encaisse/réglé :", size=11, color=ft.colors.GREY_300),
                                    ft.Text(f"{bilan['total_paye']:.2f} €", size=11, weight=ft.FontWeight.BOLD, color=ft.colors.GREEN_300)
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Row([
                                    ft.Text("État de la cotisation :", size=11, color=ft.colors.GREY_300),
                                    ft.Text(bilan["badge_texte"], size=11, weight=ft.FontWeight.BOLD, color=bilan["color"])
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                ft.Divider(height=5, color=ft.colors.GREY_700),
                                ft.Text("Versements effectués :", size=12, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_200),
                                ft.Column(controls=liste_widgets_reglements, spacing=8)
                            ], spacing=6)
                        ),

                        ft.Container(
                            padding=12,
                            bgcolor="#111827",
                            border_radius=10,
                            content=ft.Column([
                                ft.Text("Informations Personnelles", weight=ft.FontWeight.BOLD, size=13, color=ft.colors.BLUE_200),
                                ft.Divider(height=5, color=ft.colors.GREY_800),
                                self.creer_ligne_detail("📞 Tél :", m.get("telephone", "N/A")),
                                self.creer_ligne_detail("📧 Email :", m.get("email", "N/A")),
                                self.creer_ligne_detail("📍 Adresse :", adresse, multiline=True),
                                self.creer_ligne_detail("👤 Responsable :", m.get("responsable_legal", "Majeur")),
                                self.creer_ligne_detail("📜 Certif médical :", "✅ OK" if m.get("certificat_medical_valide") else "❌ MANQUANT", color_val=ft.colors.GREEN_400 if m.get("certificat_medical_valide") else ft.colors.RED_400),
                                self.creer_ligne_detail("🩺 Urgences :", "Autorisé" if m.get("accord_parental_soins") else "Non signé", color_val=ft.colors.BLUE_300 if m.get("accord_parental_soins") else ft.colors.ORANGE_300),
                                self.creer_ligne_detail("⚠️ Allergies :", m.get("allergies", "RAS"), color_val=ft.colors.RED_300 if m.get("allergies") else ft.colors.WHITE),
                                self.creer_ligne_detail("🥋 Grade :", m.get("grade_actuel", "Blanche")),
                                self.creer_ligne_detail("🆔 Licence FFK :", f"{m.get('licence_ffk', 'N/A')} ({'✅ Prise' if m.get('licence_prise_ffk') else '❌ Non prise'})"),
                            ], spacing=6)
                        )
                    ]
                )
            ),
            actions=[
                ft.TextButton("Fermer", on_click=lambda e: setattr(dialog_details, "open", False) or (self.page or self.app.page).update())
            ]
        )
        if page_obj:
            if dialog_details not in page_obj.overlay:
                page_obj.overlay.append(dialog_details)
            dialog_details.open = True
            page_obj.update()

    def creer_ligne_detail(self, label, valeur, multiline=False, color_val=ft.colors.WHITE):
        val_text = ft.Text(valeur, size=12, weight=ft.FontWeight.BOLD if not multiline else ft.FontWeight.NORMAL, color=color_val, selectable=True, expand=True)
        if multiline:
            return ft.Column([
                ft.Text(label, size=11, color=ft.colors.BLUE_200, italic=True),
                ft.Container(content=val_text, padding=ft.padding.only(left=8))
            ], spacing=2)
        return ft.Row([
            ft.Text(label, size=11, color=ft.colors.BLUE_200, italic=True, width=120),
            val_text
        ], alignment=ft.MainAxisAlignment.START)

    # ============================================================
    # ⚙️ FONCTIONS AUXILIAIRES
    # ============================================================

    def on_photo_picked(self, e: ft.FilePickerResultEvent):
        if e.files:
            self.input_photo.value = e.files[0].path
            if self.page:
                self.update()

    def filtrer_membres(self, e):
        txt = self.input_recherche.value or ""
        filtre_cotis = self.dropdown_filtre_cotis.value or "Tous"
        self.load_membres_table(filtre_texte=txt, filtre_cotis=filtre_cotis)
        if self.page:
            self.table_membres.update()

    def pre_remplir_formulaire(self, index):
        m = self.app.membres[index]
        self.input_nom.value = m.get("nom", "")
        self.input_prenom.value = m.get("prenom", "")
        self.dropdown_sexe.value = m.get("sexe", "H")
        self.input_date_naissance.value = m.get("date_naissance", "")
        self.input_photo.value = m.get("photo", "")
        self.input_email.value = m.get("email", "")
        self.input_telephone.value = m.get("telephone", "")
        self.input_rue.value = m.get("adresse_rue", "")
        self.input_cp.value = m.get("adresse_cp", "")
        self.input_ville.value = m.get("adresse_ville", "")
        self.input_responsable.value = m.get("responsable_legal", "")
        self.check_medical.value = m.get("certificat_medical_valide", False)
        self.check_accord_soins.value = m.get("accord_parental_soins", False)
        self.input_allergies.value = m.get("allergies", "")
        self.input_fiche_medecin.value = m.get("fiche_medecin", "")
        self.input_licence.value = m.get("licence_ffk", "")
        self.check_licence_prise_ffk.value = m.get("licence_prise_ffk", False)
        self.dropdown_grade.value = m.get("grade_actuel", "Blanche (6ème Kyu)")
        self.input_historique_licences.value = m.get("historique_licences", "")

    def vider_formulaire(self):
        self.input_nom.value = ""
        self.input_prenom.value = ""
        self.dropdown_sexe.value = "H"
        self.input_date_naissance.value = ""
        self.input_photo.value = ""
        self.input_email.value = ""
        self.input_telephone.value = ""
        self.input_rue.value = ""
        self.input_cp.value = ""
        self.input_ville.value = ""
        self.input_responsable.value = ""
        self.check_medical.value = False
        self.check_accord_soins.value = False
        self.input_allergies.value = ""
        self.input_fiche_medecin.value = ""
        self.input_licence.value = ""
        self.check_licence_prise_ffk.value = False
        self.dropdown_grade.value = "Blanche (6ème Kyu)"
        self.input_historique_licences.value = ""
