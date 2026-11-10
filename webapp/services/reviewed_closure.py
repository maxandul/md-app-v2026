"""Close the campaign only against the exact reviewed remaining work."""
import json
from . import export_closure_views as views,cycles,part_responsibilities as parts
from .outlook_lock import serialized_goal_delivery


@serialized_goal_delivery
def apply(db,cycle_id,*,expected,request_key,reason,owner,checked,user_id=None):
    db.execute('BEGIN IMMEDIATE')
    try:
        previous=db.execute("SELECT 1 FROM audit_log WHERE action='cycle_closure_reviewed' AND object_id=? AND json_extract(details_json,'$.request_key')=?",(str(cycle_id),request_key)).fetchone()
        if previous:
            db.rollback();return False
        plan=views.closure_plan(db,cycle_id)
        if plan['fingerprint']!=expected:raise ValueError('Die Abschlussgrundlage hat sich inzwischen geändert. Bitte die offenen Aufgaben neu prüfen.')
        if plan['cycle']['status']!='ruecklauf':raise ValueError('Der dokumentierte Abschluss ist aus der Rücklaufphase möglich.')
        if any(plan['summary'].values()) and (not reason.strip() or not owner.strip()):raise ValueError('Für verbleibende Aufgaben bitte Begründung und verantwortliche Person angeben.')
        if not checked:raise ValueError('Bitte die Dossierübergabe und externe SAP-Verarbeitung prüfen.')
        db.execute("INSERT INTO audit_log(user_id,action,object_type,object_id,details_json,created_at) VALUES (?,'cycle_closure_reviewed','cycle',?,?,?)",
            (user_id,str(cycle_id),json.dumps({'request_key':request_key,'fingerprint':expected,'summary':plan['summary'],'reason':reason,'owner':owner},ensure_ascii=False),parts.stamp()))
        cycles.change_cycle_status(db,cycle_id=cycle_id,new_status='abgeschlossen',external_checked=checked,closure_reason=reason,closure_owner=owner)
        return True
    except Exception:
        db.rollback();raise
