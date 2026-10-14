"""Post-traitement du .docx produit par pandoc : mise en page A4, pied de page, largeurs de tableaux."""
import re
import shutil
import sys
import zipfile

SRC, DST = sys.argv[1], sys.argv[2]
LARGEUR = 9638  # A4 (11906) - 2 x 2 cm (1134)

z = zipfile.ZipFile(SRC)
files = {n: z.read(n) for n in z.namelist()}
doc = files["word/document.xml"].decode("utf-8")


def texte(xml):
    return "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml))


def ajuster_tableau(m):
    tbl = m.group(0)
    lignes = re.findall(r"<w:tr>.*?</w:tr>|<w:tr .*?</w:tr>", tbl, re.S)
    if not lignes:
        return tbl
    ncol = len(re.findall(r"<w:gridCol ", tbl))
    somme = [0.0] * ncol
    mot = [0] * ncol
    for tr in lignes:
        cells = re.findall(r"<w:tc>.*?</w:tc>", tr, re.S)
        for k, c in enumerate(cells[:ncol]):
            t = texte(c)
            somme[k] += min(len(t), 160)
            mot[k] = max(mot[k], min(max((len(w) for w in t.split()), default=1), 24))
    nl = max(len(lignes), 1)
    poids = [max(somme[k] / nl + mot[k] * 2.2, 8) for k in range(ncol)]
    tot = sum(poids)
    larg = [int(LARGEUR * p / tot) for p in poids]
    mini = 1100 if ncol <= 4 else 900
    for k in range(ncol):
        if larg[k] < mini:
            larg[k] = mini
    excedent = sum(larg) - LARGEUR
    if excedent:
        k = larg.index(max(larg))
        larg[k] -= excedent
    tbl = re.sub(r'<w:tblW [^>]*/>', f'<w:tblW w:type="dxa" w:w="{LARGEUR}" />', tbl, count=1)
    tbl = re.sub(r"<w:tblGrid>.*?</w:tblGrid>",
                 "<w:tblGrid>" + "".join(f'<w:gridCol w:w="{w}" />' for w in larg) + "</w:tblGrid>",
                 tbl, count=1, flags=re.S)

    def ligne(trm):
        tr = trm.group(0)
        idx = [0]

        def cell(cm):
            k = idx[0]
            idx[0] += 1
            w = larg[k] if k < ncol else larg[-1]
            return cm.group(0).replace("<w:tcPr />", f'<w:tcPr><w:tcW w:w="{w}" w:type="dxa" /></w:tcPr>', 1)
        return re.sub(r"<w:tc>.*?</w:tc>", cell, tr, flags=re.S)
    tbl = re.sub(r"<w:tr>.*?</w:tr>|<w:tr .*?</w:tr>", ligne, tbl, flags=re.S)
    # Ne pas couper une ligne de tableau sur deux pages
    tbl = tbl.replace('<w:trPr><w:tblHeader w:val="true" /></w:trPr>',
                      '<w:trPr><w:cantSplit /><w:tblHeader w:val="true" /></w:trPr>')
    tbl = re.sub(r"<w:tr>(?!<w:trPr>)", "<w:tr><w:trPr><w:cantSplit /></w:trPr>", tbl)
    return tbl


doc = re.sub(r"<w:tbl>.*?</w:tbl>", ajuster_tableau, doc, flags=re.S)

# Images : centrées
doc = re.sub(r'(<w:p>)(<w:pPr><w:pStyle w:val="(?:CaptionedFigure|Figure|BodyText|FirstParagraph)" /></w:pPr>)?(<w:r><w:drawing>)',
             r'<w:p><w:pPr><w:jc w:val="center" /></w:pPr>\3', doc)

# Section : A4, marges 2 cm, pied de page (sauf page de titre)
sect = ('<w:sectPr><w:footerReference w:type="default" r:id="rIdPied1" />'
        '<w:pgSz w:w="11906" w:h="16838" />'
        '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="567" w:footer="567" w:gutter="0" />'
        '<w:titlePg /></w:sectPr>')
doc = re.sub(r"<w:sectPr.*?</w:sectPr>", "", doc, flags=re.S)
doc = doc.replace("</w:body>", sect + "</w:body>")
if 'xmlns:r=' not in doc[:2000]:
    doc = doc.replace("<w:document ", '<w:document xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" ', 1)
files["word/document.xml"] = doc.encode("utf-8")

pied = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:p><w:pPr><w:pBdr><w:top w:val="single" w:sz="4" w:space="4" w:color="B4C6E7"/></w:pBdr>'
        '<w:tabs><w:tab w:val="right" w:pos="9638"/></w:tabs><w:spacing w:after="0"/></w:pPr>'
        '<w:r><w:rPr><w:color w:val="7F7F7F"/><w:sz w:val="17"/></w:rPr><w:t xml:space="preserve">SmartCampus ISTC — Documentation complète</w:t></w:r>'
        '<w:r><w:rPr><w:color w:val="7F7F7F"/><w:sz w:val="17"/></w:rPr><w:tab/><w:t xml:space="preserve">Page </w:t></w:r>'
        '<w:r><w:rPr><w:color w:val="7F7F7F"/><w:sz w:val="17"/></w:rPr><w:fldChar w:fldCharType="begin"/></w:r>'
        '<w:r><w:rPr><w:color w:val="7F7F7F"/><w:sz w:val="17"/></w:rPr><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>'
        '<w:r><w:rPr><w:color w:val="7F7F7F"/><w:sz w:val="17"/></w:rPr><w:fldChar w:fldCharType="separate"/></w:r>'
        '<w:r><w:rPr><w:color w:val="7F7F7F"/><w:sz w:val="17"/></w:rPr><w:t>1</w:t></w:r>'
        '<w:r><w:rPr><w:color w:val="7F7F7F"/><w:sz w:val="17"/></w:rPr><w:fldChar w:fldCharType="end"/></w:r>'
        '</w:p></w:ftr>')
files["word/footer1.xml"] = pied.encode("utf-8")
rels = files["word/_rels/document.xml.rels"].decode()
rels = rels.replace("</Relationships>",
                    '<Relationship Id="rIdPied1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/></Relationships>')
files["word/_rels/document.xml.rels"] = rels.encode()
ct = files["[Content_Types].xml"].decode()
ct = ct.replace("</Types>", '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>')
files["[Content_Types].xml"] = ct.encode()

# Styles : le sommaire commence sur une nouvelle page
st = files["word/styles.xml"].decode()
st = re.sub(r'(<w:style [^>]*w:styleId="TOCHeading".*?<w:pPr>)', r'\1<w:pageBreakBefore/>', st, count=1, flags=re.S)
files["word/styles.xml"] = st.encode()

with zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED) as out:
    for n, data in files.items():
        out.writestr(n, data)
print("ok", DST)
