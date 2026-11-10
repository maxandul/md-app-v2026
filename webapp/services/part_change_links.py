"""UI links and labels kept outside the responsibility mutation service."""
from flask import url_for


def enrich(db,value,back):
    effects=value['effects']
    for row in effects['files']:
        if row['kind']=='regular':row['href']=url_for('main.dispatch_package',package_id=row['id'])
        elif row['kind']=='person':row['href']=url_for('main.person_word_correction',cycle_id=value['part']['cycle_id'],case_id=value['part']['case_id'],back=back,_anchor='correction-'+str(row['id']))
        else:row['href']=url_for('goal_work.dispatch',dispatch_id=row['id'],back=back)
    for row in effects['evidence']:
        if row.get('pending_import_id'):
            found=db.execute('SELECT original_filename FROM word_pdf_imports WHERE id=?',(row['pending_import_id'],)).fetchone()
            row.update(label=found[0] if found else 'PDF-Eingang',href=url_for('main.word_pdf_review',import_id=row['pending_import_id'],back=back))
        elif row.get('document_id'):
            row.update(label='Vorhandenen Rücklauf prüfen',href=url_for('return_work.detail',document_id=row['document_id'],back=back))
        elif row.get('unassigned_attachment_id'):
            found=db.execute('SELECT a.original_filename,m.subject FROM inbound_mail_attachments a JOIN inbound_mail_messages m ON m.id=a.mail_message_id WHERE a.id=?',(row['unassigned_attachment_id'],)).fetchone()
            row.update(label=found['original_filename'] if found else 'Mailanhang prüfen',href=url_for('main.returns_overview',cycle_id='',tab='mail',mail_status='all',mail_q=found['subject'] if found else '')+'#postfach')
    return value
