from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import qrcode
import io
import base64
from reportlab.platypus import Image as RLImage
from datetime import datetime


# Couleurs ChainCacao
TEAL       = HexColor('#0F6E56')
TEAL_LIGHT = HexColor('#E1F5EE')
AMBER      = HexColor('#BA7517')
GRAY       = HexColor('#888780')
DARK       = HexColor('#2C2C2A')
RED        = HexColor('#A32D2D')
GREEN      = HexColor('#1D9E75')


def generer_certificat_eudr(lot, transferts, blockchain_data: dict) -> bytes:
    """
    Génère un certificat PDF de traçabilité conforme EUDR.
    Retourne les bytes du PDF.
    """
    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(
        buffer,
        pagesize    = A4,
        rightMargin = 2*cm,
        leftMargin  = 2*cm,
        topMargin   = 2*cm,
        bottomMargin= 2*cm
    )

    styles  = getSampleStyleSheet()
    content = []

    # ── Style personnalisés ──
    style_titre = ParagraphStyle(
        'titre', parent=styles['Normal'],
        fontSize=22, textColor=white,
        alignment=TA_CENTER, fontName='Helvetica-Bold',
        spaceAfter=4
    )
    style_sous_titre = ParagraphStyle(
        'sous_titre', parent=styles['Normal'],
        fontSize=11, textColor=TEAL_LIGHT,
        alignment=TA_CENTER, fontName='Helvetica',
    )
    style_section = ParagraphStyle(
        'section', parent=styles['Normal'],
        fontSize=12, textColor=white,
        fontName='Helvetica-Bold',
        spaceBefore=4, spaceAfter=4,
    )
    style_label = ParagraphStyle(
        'label', parent=styles['Normal'],
        fontSize=9, textColor=GRAY,
        fontName='Helvetica',
    )
    style_valeur = ParagraphStyle(
        'valeur', parent=styles['Normal'],
        fontSize=11, textColor=DARK,
        fontName='Helvetica-Bold',
    )
    style_small = ParagraphStyle(
        'small', parent=styles['Normal'],
        fontSize=8, textColor=GRAY,
        fontName='Helvetica',
        alignment=TA_CENTER
    )
    style_hash = ParagraphStyle(
        'hash', parent=styles['Normal'],
        fontSize=7, textColor=GRAY,
        fontName='Courier',
    )

    # ══════════════════════════════
    # EN-TÊTE
    # ══════════════════════════════
    entete_data = [[
        Paragraph("🍫  ChainCacao", style_titre),
    ]]
    entete_table = Table(entete_data, colWidths=[17*cm])
    entete_table.setStyle(TableStyle([
        ('BACKGROUND',  (0,0), (-1,-1), TEAL),
        ('ROUNDEDCORNERS', [8]),
        ('TOPPADDING',  (0,0), (-1,-1), 16),
        ('BOTTOMPADDING',(0,0),(-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 20),
    ]))
    content.append(entete_table)

    sous_titre_data = [[Paragraph("Certificat de Traçabilité — Conformité EUDR 2025", style_sous_titre)]]
    sous_titre_table = Table(sous_titre_data, colWidths=[17*cm])
    sous_titre_table.setStyle(TableStyle([
        ('BACKGROUND',  (0,0), (-1,-1), TEAL),
        ('BOTTOMPADDING',(0,0),(-1,-1), 16),
        ('TOPPADDING',  (0,0), (-1,-1), 0),
    ]))
    content.append(sous_titre_table)
    content.append(Spacer(1, 0.5*cm))

    # Badge EUDR
    eudr_conforme = blockchain_data.get('enregistre_sur_bc', False)
    badge_color   = GREEN if eudr_conforme else AMBER
    badge_text    = "✅  CONFORME EUDR 2025" if eudr_conforme else "⏳  EN ATTENTE DE VÉRIFICATION BLOCKCHAIN"
    badge_style   = ParagraphStyle(
        'badge', parent=styles['Normal'],
        fontSize=13, textColor=white,
        fontName='Helvetica-Bold', alignment=TA_CENTER
    )
    badge_data  = [[Paragraph(badge_text, badge_style)]]
    badge_table = Table(badge_data, colWidths=[17*cm])
    badge_table.setStyle(TableStyle([
        ('BACKGROUND',   (0,0), (-1,-1), badge_color),
        ('TOPPADDING',   (0,0), (-1,-1), 10),
        ('BOTTOMPADDING',(0,0), (-1,-1), 10),
        ('ROUNDEDCORNERS', [6]),
    ]))
    content.append(badge_table)
    content.append(Spacer(1, 0.6*cm))

    # ══════════════════════════════
    # INFORMATIONS DU LOT
    # ══════════════════════════════
    section_header("📦  Informations du Lot", content, style_section, TEAL)

    lot_rows = [
        ["Identifiant du lot",  str(lot.id)],
        ["Espèce",              lot.get_espece_display()],
        ["Poids à la récolte",  f"{lot.poids_kg} kg"],
        ["Date de récolte",     lot.date_recolte.strftime("%d/%m/%Y")],
        ["Coordonnées GPS",     f"Lat: {lot.gps_latitude}° / Lng: {lot.gps_longitude}°"],
        ["Statut actuel",       lot.get_statut_display()],
    ]
    content.append(build_info_table(lot_rows, style_label, style_valeur))
    content.append(Spacer(1, 0.5*cm))

    # ══════════════════════════════
    # INFORMATIONS DE L'AGRICULTEUR
    # ══════════════════════════════
    section_header("👨‍🌾  Agriculteur Producteur", content, style_section, TEAL)

    agri = lot.agriculteur
    agri_rows = [
        ["Nom d'utilisateur", agri.username],
        ["Village",           agri.village or "—"],
        ["Région",            agri.region  or "—"],
        ["Téléphone",         agri.telephone or "—"],
    ]
    content.append(build_info_table(agri_rows, style_label, style_valeur))
    content.append(Spacer(1, 0.5*cm))

    # ══════════════════════════════
    # HISTORIQUE DES TRANSFERTS
    # ══════════════════════════════
    section_header("🔄  Historique des Transferts", content, style_section, TEAL)

    if transferts:
        transfert_header = [
            Paragraph("Étape", ParagraphStyle('th', fontSize=9, textColor=white, fontName='Helvetica-Bold')),
            Paragraph("Expéditeur", ParagraphStyle('th', fontSize=9, textColor=white, fontName='Helvetica-Bold')),
            Paragraph("Destinataire", ParagraphStyle('th', fontSize=9, textColor=white, fontName='Helvetica-Bold')),
            Paragraph("Poids vérifié", ParagraphStyle('th', fontSize=9, textColor=white, fontName='Helvetica-Bold')),
            Paragraph("Date", ParagraphStyle('th', fontSize=9, textColor=white, fontName='Helvetica-Bold')),
        ]
        transfert_rows = [transfert_header]

        etapes_labels = {
            'ferme_cooperative':          'Ferme → Coopérative',
            'cooperative_transformateur': 'Coopérative → Transformateur',
            'transformateur_exportateur': 'Transformateur → Exportateur',
            'exportateur_europe':         'Exportateur → Europe',
        }
        cell_style = ParagraphStyle('cell', fontSize=8, textColor=DARK, fontName='Helvetica')

        for t in transferts:
            transfert_rows.append([
                Paragraph(etapes_labels.get(t.etape, t.etape), cell_style),
                Paragraph(t.expediteur.username, cell_style),
                Paragraph(t.destinataire.username, cell_style),
                Paragraph(f"{t.poids_verifie} kg", cell_style),
                Paragraph(t.date_transfert.strftime("%d/%m/%Y %H:%M"), cell_style),
            ])

        t_table = Table(transfert_rows, colWidths=[4.5*cm, 3*cm, 3*cm, 2.5*cm, 3.5*cm])
        t_table.setStyle(TableStyle([
            ('BACKGROUND',   (0,0), (-1,0),  TEAL),
            ('BACKGROUND',   (0,1), (-1,-1), TEAL_LIGHT),
            ('ROWBACKGROUNDS',(0,1),(-1,-1), [white, TEAL_LIGHT]),
            ('GRID',         (0,0), (-1,-1), 0.5, HexColor('#D3D1C7')),
            ('TOPPADDING',   (0,0), (-1,-1), 6),
            ('BOTTOMPADDING',(0,0), (-1,-1), 6),
            ('LEFTPADDING',  (0,0), (-1,-1), 8),
        ]))
        content.append(t_table)
    else:
        content.append(Paragraph("Aucun transfert enregistré.", style_label))

    content.append(Spacer(1, 0.5*cm))

    # ══════════════════════════════
    # PREUVE BLOCKCHAIN
    # ══════════════════════════════
    section_header("⛓️  Preuve Blockchain", content, style_section, TEAL)

    tx_hash = lot.tx_hash or "Non enregistré"
    bc_rows = [
        ["Transaction Hash (lot)",  tx_hash],
        ["Enregistré sur blockchain", "Oui ✅" if eudr_conforme else "Non ⏳"],
        ["Réseau",                  "Polygon Amoy (Testnet)"],
        ["Vérification",            f"https://amoy.polygonscan.com/tx/0x{tx_hash}"],
    ]

    bc_style_hash = ParagraphStyle(
        'bc_hash', parent=styles['Normal'],
        fontSize=7, textColor=DARK, fontName='Courier'
    )
    bc_rows_para = []
    for label, val in bc_rows:
        bc_rows_para.append([
            Paragraph(label, style_label),
            Paragraph(val, bc_style_hash if 'Hash' in label or 'Vérification' in label else style_valeur)
        ])

    bc_table = Table(bc_rows_para, colWidths=[5*cm, 12*cm])
    bc_table.setStyle(TableStyle([
        ('BACKGROUND',   (0,0), (-1,-1), TEAL_LIGHT),
        ('GRID',         (0,0), (-1,-1), 0.5, HexColor('#D3D1C7')),
        ('TOPPADDING',   (0,0), (-1,-1), 6),
        ('BOTTOMPADDING',(0,0), (-1,-1), 6),
        ('LEFTPADDING',  (0,0), (-1,-1), 8),
    ]))
    content.append(bc_table)
    content.append(Spacer(1, 0.5*cm))

    # ══════════════════════════════
    # QR CODE
    # ══════════════════════════════
    section_header("📱  QR Code de Vérification", content, style_section, TEAL)

    verify_url = f"http://localhost:8000/api/lots/{lot.id}/verify/"
    qr_img     = generer_qr_image(verify_url)

    qr_table = Table(
        [[qr_img, Paragraph(
            f"Scannez ce QR code pour vérifier\nl'authenticité de ce certificat\nen temps réel.\n\n{verify_url}",
            ParagraphStyle('qr_text', fontSize=9, textColor=DARK, fontName='Helvetica', leading=14)
        )]],
        colWidths=[5*cm, 12*cm]
    )
    qr_table.setStyle(TableStyle([
        ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING',  (0,0), (-1,-1), 8),
        ('TOPPADDING',   (0,0), (-1,-1), 8),
        ('BOTTOMPADDING',(0,0), (-1,-1), 8),
        ('BACKGROUND',   (0,0), (-1,-1), TEAL_LIGHT),
        ('ROUNDEDCORNERS', [6]),
    ]))
    content.append(qr_table)
    content.append(Spacer(1, 0.8*cm))

    # ══════════════════════════════
    # PIED DE PAGE
    # ══════════════════════════════
    content.append(HRFlowable(width="100%", thickness=1, color=TEAL))
    content.append(Spacer(1, 0.2*cm))

    footer_data = [[
        Paragraph(f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", style_small),
        Paragraph("ChainCacao — Miabe Hackathon 2026", style_small),
        Paragraph("Darollo Technologies Corporation", style_small),
    ]]
    footer_table = Table(footer_data, colWidths=[5.6*cm, 5.7*cm, 5.7*cm])
    footer_table.setStyle(TableStyle([
        ('TOPPADDING',   (0,0), (-1,-1), 4),
        ('ALIGN',        (0,0), (0,0),   'LEFT'),
        ('ALIGN',        (1,0), (1,0),   'CENTER'),
        ('ALIGN',        (2,0), (2,0),   'RIGHT'),
    ]))
    content.append(footer_table)

    doc.build(content)
    return buffer.getvalue()


# ── Fonctions utilitaires ──

def section_header(title, content, style, color):
    data  = [[Paragraph(title, style)]]
    table = Table(data, colWidths=[17*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND',   (0,0), (-1,-1), color),
        ('TOPPADDING',   (0,0), (-1,-1), 8),
        ('BOTTOMPADDING',(0,0), (-1,-1), 8),
        ('LEFTPADDING',  (0,0), (-1,-1), 12),
        ('ROUNDEDCORNERS', [4]),
    ]))
    content.append(table)
    content.append(Spacer(1, 0.3*cm))


def build_info_table(rows, style_label, style_valeur):
    data = [
        [Paragraph(label, style_label), Paragraph(str(val), style_valeur)]
        for label, val in rows
    ]
    table = Table(data, colWidths=[5*cm, 12*cm])
    table.setStyle(TableStyle([
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [HexColor('#F1EFE8'), white]),
        ('GRID',          (0,0), (-1,-1), 0.5, HexColor('#D3D1C7')),
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
    ]))
    return table


def generer_qr_image(url: str):
    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img    = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return RLImage(buffer, width=3.5*cm, height=3.5*cm)