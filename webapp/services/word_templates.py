"""Befüllt freigegebene Word-Vorlagen, ohne zusätzliche Laufzeitabhängigkeit."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from datetime import date
from xml.dom import minidom
from xml.parsers.expat import ExpatError
from zipfile import ZipFile, BadZipFile, ZIP_DEFLATED
import re

from .legacy_forms import COMPETENCY_TAGS

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _children(node, local):
    return [n for n in node.childNodes if n.nodeType == n.ELEMENT_NODE and n.namespaceURI == W and n.localName == local]


def _all(node, local):
    return list(node.getElementsByTagNameNS(W, local))


def _attr(node, key):
    return node.getAttributeNS(W, key)


class WordTemplate:
    def __init__(self, path: Path):
        try:
            self.raw = path.read_bytes()
            with ZipFile(BytesIO(self.raw)) as archive:
                if sum(info.file_size for info in archive.infolist()) > 50 * 1024 * 1024:
                    raise ValueError("Die entpackte Word-Vorlage ist zu gross.")
                xml = archive.read("word/document.xml")
            if b"<!DOCTYPE" in xml or b"<!ENTITY" in xml:
                raise ValueError("Die Word-Vorlage enthält nicht unterstützte XML-Deklarationen.")
            self.doc = minidom.parseString(xml)
        except (OSError, BadZipFile, KeyError, ExpatError) as exc:
            raise ValueError(f"Word-Vorlage nicht lesbar: {path.name}") from exc
        self.next_id = max([int(_attr(n, "val")) for n in _all(self.doc, "id") if _attr(n, "val").isdigit()] or [0]) + 1
        # Die freigegebenen Vorlagen enthalten teilweise alte fullDate-Werte,
        # obwohl das sichtbare Feld leer ist. Unausgefüllte Termine bleiben leer.
        for node in _all(self.doc, "date"):
            if node.hasAttributeNS(W, "fullDate"):
                node.removeAttributeNS(W, "fullDate")

    def control(self, tag):
        found = []
        for control in _all(self.doc, "sdt"):
            props = _children(control, "sdtPr")
            tags = _children(props[0], "tag") if props else []
            if tags and _attr(tags[0], "val") == tag:
                found.append(control)
        if len(found) != 1:
            raise ValueError(f"Vorlagenfeld «{tag}» fehlt oder ist mehrfach vorhanden.")
        return found[0]

    def new(self, local):
        return self.doc.createElementNS(W, "w:" + local)

    def fill(self, tag, value, *, goal=False, keep_with_next=False):
        control = self.control(tag)
        props = _children(control, "sdtPr")[0]
        content = _children(control, "sdtContent")[0]
        for local in ("showingPlcHdr", "dataBinding"):
            for node in _children(props, local):
                props.removeChild(node)
        old_runs = _all(content, "rPr")
        run_style = old_runs[0].cloneNode(True) if old_runs else self.new("rPr")
        for local in ("color", "vanish", "webHidden"):
            for node in _children(run_style, local):
                run_style.removeChild(node)
        color = self.new("color"); color.setAttributeNS(W, "w:val", "000000"); run_style.appendChild(color)
        if goal:
            for local in ("sz", "szCs"):
                for node in _children(run_style, local):
                    run_style.removeChild(node)
                size = self.new(local)
                size.setAttributeNS(W, "w:val", "18")
                run_style.appendChild(size)
        cell = _children(content, "tc")
        paragraphs = _all(content, "p")
        paragraph_style = _children(paragraphs[0], "pPr") if paragraphs else []
        paragraph_style = paragraph_style[0].cloneNode(True) if paragraph_style else None
        if goal:
            if paragraph_style is None:
                paragraph_style = self.new("pPr")
            for node in _children(paragraph_style, "keepNext"):
                paragraph_style.removeChild(node)
            keep = self.new("keepNext")
            keep.setAttributeNS(W, "w:val", "1" if keep_with_next else "0")
            paragraph_style.appendChild(keep)
        if cell:
            destination = cell[0]
            for node in list(destination.childNodes):
                if node not in _children(destination, "tcPr"):
                    destination.removeChild(node)
        else:
            destination = content
            for node in list(content.childNodes):
                content.removeChild(node)
        if cell or paragraphs:
            paragraph = self.new("p")
            if paragraph_style is not None:
                paragraph.appendChild(paragraph_style)
            destination.appendChild(paragraph)
            destination = paragraph
        # Listenzeichen und Absätze werden als einheitlicher Text übernommen.
        value = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
        for index, line in enumerate(value.split("\n")):
            run = self.new("r"); run.appendChild(run_style.cloneNode(True))
            if index:
                run.appendChild(self.new("br"))
            text = self.new("t")
            text.setAttribute("xml:space", "preserve")
            text.appendChild(self.doc.createTextNode(line))
            run.appendChild(text); destination.appendChild(run)
        for node in _children(props, "date"):
            if value:
                day = date.fromisoformat("-".join(reversed(value.split("."))))
                node.setAttributeNS(W, "w:fullDate", day.isoformat() + "T00:00:00Z")
        if tag == "rb_nebenbeschaeftigung":
            row = control.parentNode
            while row is not None and not (row.nodeType == row.ELEMENT_NODE and row.namespaceURI == W and row.localName == "tr"):
                row = row.parentNode
            if row is not None:
                row_props = _children(row, "trPr")
                if not row_props:
                    row.insertBefore(self.new("trPr"), row.firstChild)
                    row_props = _children(row, "trPr")
                if not _children(row_props[0], "cantSplit"):
                    row_props[0].appendChild(self.new("cantSplit"))

    def goals(self, tags, goals):
        first = self.control(tags[0])
        row = first
        while row is not None and not (row.nodeType == row.ELEMENT_NODE and row.namespaceURI == W and row.localName == "tr"):
            row = row.parentNode
        if row is None:
            raise ValueError("Das Ziel-Vorlagenfeld liegt nicht in einer Tabellenzeile.")
        # Wiederholte Tabellenköpfe müssen vom Tabellenanfang an zusammenhängend
        # markiert sein. Bei Entwicklungszielen gehört die Kompetenz dazu.
        for header in _children(row.parentNode, "tr"):
            if header == row:
                break
            props = _children(header, "trPr")
            if not props:
                header.insertBefore(self.new("trPr"), header.firstChild)
                props = _children(header, "trPr")
            if not _children(props[0], "tblHeader"):
                props[0].appendChild(self.new("tblHeader"))
        for tag in tags:
            node = self.control(tag)
            while node is not None and node != row:
                node = node.parentNode
            if node is None:
                raise ValueError("Die vier Zielfelder liegen nicht in derselben Tabellenzeile.")
        empty = row.cloneNode(True)
        previous = row
        for index, goal in enumerate(goals or [{}], start=1):
            current_tags = tags
            if index > 1:
                new_row = empty.cloneNode(True)
                for node in _all(new_row, "id"):
                    node.setAttributeNS(W, "w:val", str(self.next_id)); self.next_id += 1
                for node in _all(new_row, "tag"):
                    node.setAttributeNS(W, "w:val", _attr(node, "val").rsplit("_", 1)[0] + "_" + str(index))
                row.parentNode.insertBefore(new_row, previous.nextSibling)
                previous = new_row
                current_tags = [tag.rsplit("_", 1)[0] + "_" + str(index) for tag in tags]
            for tag, key in zip(current_tags, ("title", "criteria", "steps", "target_date")):
                value = str(goal.get(key, "") or "")
                if key == "title" and value and not re.match(r"^\d+[.)]\s", value):
                    value = f"{index}. {value}"
                # Das letzte Entwicklungsziel bleibt bei seiner Einschätzung.
                keep = "_vorjahr_ziel_" in tags[0] and index == max(1, len(goals))
                self.fill(tag, value, goal=True, keep_with_next=keep)

    def to_bytes(self):
        output = BytesIO()
        with ZipFile(BytesIO(self.raw)) as source, ZipFile(output, "w", ZIP_DEFLATED) as result:
            for info in source.infolist():
                result.writestr(info, self.doc.toxml(encoding="UTF-8") if info.filename == "word/document.xml" else source.read(info.filename))
        return output.getvalue()


def render_word_form(template_path: Path, *, kind: str, fields: dict, performance_goals=(), development_goals=()) -> bytes:
    prefix = {"review": "rb", "outlook": "ab", "probation": "pz"}[kind]
    template = WordTemplate(template_path)
    for suffix in ("name", "pn", "funktion", "oe", "name_vg", "pn_vg", "datum_von", "datum_bis"):
        template.fill(f"{prefix}_{suffix}", fields.get(suffix, ""))
    if kind == "review":
        template.fill("rb_nebenbeschaeftigung", fields.get("nebenbeschaeftigung", ""))
        template.goals([f"rb_ziel_{suffix}_1" for suffix in ("vorjahr", "kriterien", "schritte", "termin")], performance_goals)
        by_competency = {name: [] for name in COMPETENCY_TAGS.values()}
        for goal in development_goals:
            competency = goal.get("competency", "")
            if competency not in by_competency:
                raise ValueError(f"Entwicklungsziel hat keine bekannte Kompetenz: {competency or 'leer'}.")
            by_competency[competency].append(goal)
        for tag, name in COMPETENCY_TAGS.items():
            template.goals([f"rb_{tag}_vorjahr_{suffix}_1" for suffix in ("ziel", "kriterien", "schritte", "termin")], by_competency[name])
    return template.to_bytes()
