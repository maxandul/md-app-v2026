"""Synthetic filled forms exercising the validated 2026 layout contract."""
from reportlab.pdfgen import canvas
from webapp.services.legacy_forms import COMPETENCY_TAGS


def form_pdf(path, *, kind='review', probation=False, rating='Gut', pn='111113',
             manager='111116', year=None, marker='', no_reason='', missing_page=False):
    year = year or (2026 if kind=='outlook' else 2025)
    count = 5
    c = canvas.Canvas(str(path), pagesize=(595,842), invariant=1)
    def text(x,y,value,size=9):
        c.setFillColorRGB(0,0,0);c.setFont('Helvetica',size);c.drawString(x,y,value)
    def field(x,y,w,h,value='',blue=True):
        c.setFillColorRGB(*((.882,.965,1) if blue else (.949,.949,.949)))
        c.rect(x,y,w,h,fill=1,stroke=0)
        text(x+4,y+h-13,value)
    def page(n):
        text(40,815,'Kanton Zürich');text(520,815,f'{n}/{count}')
    def wide(y,label,value=''):
        text(40,y,label);field(40,y-38,513,24,value)
    def goals(y,values,blue):
        for (x,w),value in zip([(40,150),(191,130),(322,160),(483,70)],values):
            field(x,y,w,30,value,blue)
    label='Ausblick' if kind=='outlook' else ('Rückblick auf die Probezeit' if probation else 'Rückblick')
    page(1);text(40,790,'Mitarbeitenden-Dialog (MD) - '+label)
    text(40,765,'Name: Testperson PN: '+pn)
    text(40,745,'Name VG: Testführung PN VG: '+manager)
    text(40,720,'Wird der '+label+' durchgeführt? Ja')
    text(40,695,('Ausblick' if kind=='outlook' else 'Rückblick')+f' auf: 01.01.{year} bis 31.12.{year} Gespräch vom: 15.01.{year if kind=="outlook" else year+1}')
    wide(665,'Falls nein, hier Begründung',no_reason)
    wide(605,'Gibt es allgemeine Bemerkungen?',marker or 'Gemeinsam besprochen')
    if probation:
        wide(510,'Wie wird die bisherige Leistung eingeschätzt?','Leistung erfüllt')
    else:
        text(40,520,'1. Zielvereinbarung' if kind=='outlook' else 'Leistungsziele aus dem Vorjahr')
        goals(465,['Projekt','Messung','Schritte','31.12.'],kind=='outlook')
        wide(435,'Optionales Freitext-Feld:' if kind=='outlook' else 'Leistung','Leistung erfüllt')
    c.showPage()
    names=list(COMPETENCY_TAGS.values())
    for number,group in enumerate((names[:5],names[5:10],names[10:]),2):
        page(number)
        for index,name in enumerate(group):
            y=770-index*120
            text(40,y,name)
            if probation:
                field(40,y-50,513,30,'Einschätzung '+name)
            else:
                goals(y-45,['Entwicklung','Kriterium','Schritt','30.06.'],kind=='outlook')
                if kind=='review':field(40,y-80,513,24,'Einschätzung: Besprochen')
        c.showPage()
    page(5)
    if kind=='outlook':
        text(40,770,'3. Laufbahnorientierte Entwicklung')
        text(40,740,'Besteht ein Wunsch bezüglich laufbahnorientierter Entwicklung?')
        field(460,727,93,24,'KNF I')
        wide(685,'Gibt es Bemerkungen bezüglich laufbahnorientierter Entwicklung?','Interesse geklärt')
    else:
        text(40,790,'2. Bemerkungen zum Gespräch')
        wide(765,'Gibt es Bemerkungen der vorgesetzten Person?','Besprochen')
        wide(705,'Gibt es Bemerkungen des/der Mitarbeitenden?','Besprochen')
        text(40,645,'Ist ein Gespräch mit der nächsthöheren vorgesetzten Person gewünscht? Nein')
        wide(610,'Gibt es Bemerkungen der nächsthöheren vorgesetzten Person?')
        text(40,550,'Gibt es Bemerkungen des/der Mitarbeitenden')
        text(40,537,'zum Gespräch mit der nächsthöheren vorgesetzten Person?')
        field(40,500,513,24)
        if probation:
            text(40,465,'4. Anstellungsentscheid')
            text(40,440,'Wird das Arbeitsverhältnis weitergeführt? Ja')
        else:
            text(40,465,'1.3. Gesamteindruck');text(40,440,'Der Gesamteindruck ist:')
            field(460,427,93,24,rating)
            wide(395,'Aktuell bewilligte und als derzeit ausgeübt erfasste Nebenbeschäftigungen','Keine')
            text(40,330,'Sind die oben aufgeführten Bewilligungen vollständig und aktuell?')
            field(460,317,93,24,'Ja')
            wide(280,'Falls nicht vollständig und/oder aktuell, bitte präzisieren:')
    text(40,190,'5. Bestätigung Mitarbeitenden-Dialog')
    text(40,140,'Unterschrift Mitarbeitende/r');text(320,140,'Unterschrift vorgesetzte Person')
    text(40,90,'Administratives')
    if not missing_page:c.showPage()
    c.save()
    return path
