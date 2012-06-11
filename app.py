import re, os, inspect, sys, datetime
from functools import wraps

thisPath = os.path.dirname(inspect.getfile(inspect.currentframe()))+'/'
if thisPath == '/':
    thisPath = './'
sys.path.append(thisPath+'libs/')

from flask import Flask, Response, redirect, \
        url_for, request, session, abort, \
        render_template, json, jsonify

# Google App Engine Block
try:
    import logging
    from google.appengine.api import \
            mail, users
    from google.appengine.ext.webapp.util import \
            run_wsgi_app
    from google.appengine.ext import \
            db
    run_on_google = True
except:
    run_on_google = False
# End Google App Engine Block

sites = [
        'DIST',
        'WHS',
        'EHS',
        'FVHS',
        'MHS',
        'OVHS',
        'HBHS',
        'VVHS',
        'HBAS',
        'CDS',
        'CHS',
        'Food Services',
        'Transportation',
        ]

nettechs = {
        'DIST': 'ishelp@hbuhsd.edu',
        'WHS': 'dhidalgo@hbuhsd.edu',
        'EHS': 'ptabony@hbuhsd.edu',
        'FVHS': 'iprotsenko@hbuhsd.edu',
        'MHS': 'rpowell@hbuhsd.edu',
        'OVHS': 'dtran@hbuhsd.edu',
        'HBHS': 'along@hbuhsd.edu',
        'VVHS': 'ishelp@hbuhsd.edu',
        'HBAS': 'wlacap@hbuhsd.edu',
        'CDS': 'wlacap@hbuhsd.edu',
        'CHS': 'wlacap@hbuhsd.edu',
        'Food Services': 'ishelp@hbuhsd.edu',
        'Transportation': 'ishelp@hbuhsd.edu',
        }

app = Flask(__name__)

page_params = {}

class Support_Ticket(db.Model):
    ticket_type = db.StringProperty()
    user_type = db.StringProperty()
    site = db.StringProperty()
    macro = db.StringProperty()
    micro = db.StringProperty()
    
    submitted_on = db.DateTimeProperty(auto_now_add=True)
    submitted_by = db.UserProperty()
    
    completed_on = db.DateTimeProperty()
    completed_by = db.UserProperty()

    assigned_to = db.StringProperty()
    description = db.StringProperty()
    elevated = db.BooleanProperty()

    starred = db.BooleanProperty()
    meta = db.StringListProperty()

class Note(db.Model):
    for_ticket = db.ReferenceProperty(Support_Ticket, 
            collection_name='notes')
    message = db.StringProperty()

    submitted_on = db.DateTimeProperty(auto_now_add=True)
    submitted_by = db.UserProperty()

def ticket_to_json(ticket):
    this_ticket = {
            'ticketType': ticket.ticket_type,
            'ticketUserType': ticket.user_type,
            'ticketSite': ticket.site,
            'ticketMacroLocation': ticket.macro,
            'ticketMicroLocation': ticket.micro,
            'ticketSubmittedOn': str(ticket.submitted_on)[:16],
            'ticketSubmittedBy': str(ticket.submitted_by),
            'ticketCompletedOn': str(ticket.completed_on)[:16],
            'ticketCompletedBy': str(ticket.completed_by),
            'ticketAssignedTo' : str(ticket.assigned_to),
            'ticketDescription' : ticket.description,
            'ticketElevated': ticket.elevated,
            'ticketStarred': ticket.starred,
            'ticketMeta': ticket.meta,
            'id': str(ticket.key().id()),
            }
    these_notes = [{
        'noteId': str(note.key().id()),
        'noteMessage': note.message,
        'noteSubmittedBy': str(note.submitted_by),
        'noteSubmittedOn': str(note.submitted_on)[:16],
        } for note in ticket.notes]
    this_ticket['ticketNotes'] = these_notes
    return this_ticket

@app.route('/')
def home():
    if run_on_google:
        logging.info(users.get_current_user())
        this_user = str(users.get_current_user())
        if not re.match('.*@.*', this_user):
            this_user += '@hbuhsd.edu'
    else:
        this_user = 'test@hbuhsd.edu'

    page_params['title'] = 'Ticket Manager'
    page_params['message'] = 'tickets displayed are for user %s' % this_user
    page_params['debug'] = {
            'ticketList': 'style="background-color: blue;"',
            'singleTicket': 'style="background-color: red;"',
            'ticketNotes': 'style="background-color: green;"',
            }
    return render_template('manage_tickets.html', page_params=page_params)

@app.route('/new_ticket', methods=['POST', 'GET', 'PUT', 'DELETE'])
def new_ticket():
    if run_on_google:
        logging.info(users.get_current_user())
        this_user = str(users.get_current_user())+'@hbuhsd.edu'
    else:
        this_user = 'test@hbuhsd.edu'

    if request.method == 'POST':
        logging.info(request.form)
        these_params = request.form

        if these_params['ticketSite'] in nettechs:
            set_assignment = nettechs[these_params['ticketSite']]
        else:
            set_assignment = nettechs['DIST']

        this_ticket = Support_Ticket(
                ticket_type=these_params['ticketType'],
                user_type=these_params['ticketUserType'],
                site=these_params['ticketSite'],
                macro=these_params['ticketMacroLocation'],
                micro=these_params['ticketMicroLocation'],
                description=these_params['ticketDescription'],
                submitted_by=users.get_current_user(),
                assigned_to=set_assignment,
                elevated=False,
                starred=False,
                )
        this_ticket.put()
        return jsonify({'message': 'OK'})

    page_params['sites'] = sites
    page_params['title'] = 'New Ticket'
    page_params['message'] = 'please fill all fields to submit a new support ticket'
    return render_template('new_ticket.html', page_params=page_params)

# POST = create # PUT = update # GET = retrieve # DELETE = delete # Backbone.js
@app.route('/ticket/<ticket_id>', methods=['POST', 'GET', 'PUT', 'DELETE'])
def ticket(ticket_id):
    logging.info('method: %s' % request.method)
    logging.info('ticket_id: %s' % ticket_id)
    if request.method == 'GET':
        this_query = Support_Ticket.get_by_id(int(ticket_id))
        return Response(response=json.dumps(ticket_to_json(this_query)), mimetype="application/json")

    elif request.method == 'PUT':
        these_params = request.json
        this_query = Support_Ticket.get_by_id(int(ticket_id))
        saved_notes = set([int(note.key().id()) for note in this_query.notes])
        put_notes = set([int(note['noteId']) for note in these_params['ticketNotes'] if 'noteId' in note])
        new_notes = [str(note['noteMessage']) for note in these_params['ticketNotes'] if 'noteId' not in note]
        this_query.starred = these_params['ticketStarred']

        for note in new_notes:
            Note(for_ticket=this_query,
                    message=note,
                    submitted_by=users.get_current_user()).put()

        if len(put_notes) < len(saved_notes):
            for note_to_remove in (saved_notes - put_notes):
                this_note = Note.get_by_id(int(note_to_remove))
                this_note.delete()

        this_query.put()
        return Response(response=json.dumps(ticket_to_json(Support_Ticket.get_by_id(int(ticket_id)))), mimetype="application/json")
    else:
        return jsonify({'message': 'ERROR'})

@app.route('/tickets', methods=['GET'])
def tickets():
    this_user = users.get_current_user()
    this_query = Support_Ticket.gql("WHERE submitted_by = :submitted_by", submitted_by=users.get_current_user())
    these_tickets = [ticket_to_json(ticket) for ticket in this_query]

    logging.info('this_user: %s requesting_tickets: %s' % (this_user, these_tickets))
    return Response(response=json.dumps(these_tickets), mimetype="application/json")

@app.route('/test', methods=['POST', 'GET', 'PUT', 'DELETE'])
def test():
    return jsonify({'message': 'OK'})

@app.errorhandler(404)
def page_not_found(error):
    page_params['title'] = '404'
    page_params['message'] = 'The page you are looking for cannot be found'
    return render_template('404.html', page_params=page_params)

@app.errorhandler(403)
def http_forbidden(error):
    page_params['title'] = '403'
    page_params['message'] = 'Access to this page is restricted to HBUHSD staff only. To access this page you must have a valid @hbuhsd.edu email account'
    return render_template('403.html', page_params=page_params)

if __name__ == "__main__":
    if run_on_google == False:
        app.run(
                debug=True,
                host='0.0.0.0',
                port=5000,
                )
    else:
        run_wsgi_app(app)
