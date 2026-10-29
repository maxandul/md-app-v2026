"""Nachvollziehbare Änderungen und Entscheidungen je Person einer Ausgabe."""
import hashlib
import json


def fingerprint(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()


def changes_for_package(package, manifest, current):
    old=manifest.get('source_snapshot')
    previous={c['case_id']:c for c in old['cases']} if old else {}
    current_cases={c['case_id']:c for c in current['cases']}
    docs={}
    for doc in manifest.get('documents',[]):
        docs.setdefault(doc['case_id'],set()).add(doc['kind'])
    changes=[]
    scopes={'full':'Rückblick und Ausblick','review_only':'Nur Rückblick','outlook_only':'Nur Ausblick','none':'Kein MD','':'Noch nicht festgelegt'}
    kinds={'review':'Rückblick','outlook':'Ausblick','probation':'Probezeit-Rückblick'}
    labels={'official_scope':'Pflichtumfang','suggested_scope':'Vorgeschlagener Umfang','period_start':'Zeitraum von','period_end':'Zeitraum bis','goals':'Vorjahresziele','secondary':'Nebenbeschäftigungen / öffentliche Ämter','secondary_employment':'Nebenbeschäftigungen','first_name':'Vorname','last_name':'Nachname','position':'Funktion','org_unit':'Organisationseinheit','entry_date':'Eintritt','exit_date':'Austritt','probation_end':'Probezeitende','employment_assignment':'Anstellung','event_type':'Dialogart','parts':'Zuständigkeit, Zeitraum oder Formular-OE eines zugewiesenen Gesprächsteils'}
    for key in sorted(set(previous)|set(current_cases)|set(docs)):
        before=previous.get(key);after=current_cases.get(key)
        fields=[]
        if old:
            if before is None: fields=['Person/Fall neu hinzugekommen']
            elif after is None: fields=['Person/Fall nicht mehr in dieser aktiven Führungslinie']
            else:
                fields=[]
                for k in sorted(set(before)|set(after)):
                    if before.get(k)==after.get(k):continue
                    label=labels.get(k,k)
                    if k in ('official_scope','suggested_scope'):
                        label += ': '+scopes.get(before.get(k),str(before.get(k)))+' → '+scopes.get(after.get(k),str(after.get(k)))
                    elif k not in ('goals','secondary','secondary_employment','parts'):
                        label += ': '+str(before.get(k) or 'leer')+' → '+str(after.get(k) or 'leer')
                    fields.append(label)
        elif after:
            scope=after['official_scope'] or after['suggested_scope']
            expected=set()
            if scope in ('full','review_only'):expected.add('probation' if after['event_type']=='probation_review' else 'review')
            if scope in ('full','outlook_only'):expected.add('outlook')
            if expected != docs.get(key,set()):
                fields=['Formularumfang: bisher '+', '.join(kinds.get(k,k) for k in sorted(docs.get(key,set())))+'; jetzt '+(', '.join(kinds.get(k,k) for k in sorted(expected)) or 'keine Formulare')]
        else:fields=['Person/Fall nicht mehr in dieser aktiven Führungslinie']
        if fields:
            person=after or before or {}
            changes.append({'case_id':key,'name':(person.get('first_name','')+' '+person.get('last_name','')).strip() or key,'details':'; '.join(fields),'signature':fingerprint(after),'assignment':person.get('employment_assignment',''),'can_generate':bool(after and (after['official_scope'] or after['suggested_scope'])!='none')})
    shared={k:v for k,v in current.items() if k!='cases'}
    if not old or shared!={k:v for k,v in old.items() if k!='cases'}:
        labels_shared=[]
        if not old:labels_shared=['Diese frühere Ausgabe enthält noch keinen Detailstand. Weitere Änderungen an Stammdaten, Zielen oder Vorlagen können nicht vollständig rekonstruiert werden.']
        else:
            for key,label in [('cycle','Durchlauf / SAP-Importstand'),('manager','Führungskraft / Empfänger'),('templates','Vorlagen / Beilagen'),('package_format','Ausgabeformat'),('feedback_case_ids','Reguläre Feedback-Zuordnung')]:
                if old.get(key)!=current.get(key):labels_shared.append(label)
        changes.append({'case_id':'__shared__','name':'Übergreifende Änderung / Prüfung','details':'; '.join(labels_shared),'signature':fingerprint(current if not old else shared),'can_generate':False})
    return changes


def resolve_change(db, *, package_id, case_id, signature, outcome, reason, current_changes):
    if outcome not in ('no_resend','person_corrected'):
        raise ValueError('Bitte Vorgehen wählen.')
    change=next((c for c in current_changes if c['case_id']==case_id),None)
    if not change or change['signature']!=signature:
        raise ValueError('Die Grundlagen haben sich inzwischen geändert. Ansicht neu laden und erneut prüfen.')
    from .hr_workflow import stamp
    db.execute('INSERT INTO word_change_decisions(package_id,case_id,source_signature,outcome,reason,created_at) VALUES (?,?,?,?,?,?)',
               (package_id,case_id,signature,outcome,reason.strip(),stamp()))
    db.commit()
