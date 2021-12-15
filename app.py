import csv
import json
import os
import re
import sys
from time import ctime

import flask
from flask import Flask, render_template, request
from flask.helpers import url_for
from werkzeug import datastructures
from werkzeug.utils import redirect

os.chdir(os.path.dirname(__file__))

app = Flask(__name__)

# TODO agregar lista de máquinas para hacer
# TODO agregar suma de ganancias
# TODO agregar lista de gastos
# TODO agregar lista de cliente con deudas y máquinas

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/', methods=['POST'])
def index_post():
    ID = request.form['machine']
    return redirect(f'http://192.168.1.69:5000/machine?id={ID}')

@app.route('/addmachine')
def add_machine_index():
    return render_template('add_machine.html')

@app.route('/addmachine', methods=['GET', 'POST'])
def add_new_machine():
    client = request.form['client']
    client_phone = request.form['client_phone']
    machine_model = request.form['machine_model']
    problems = request.form.get('problems', False)
    ID = add_machine(client, client_phone, machine_model, problems)
    return redirect(f'http://192.168.1.69:5000/machine?id={ID}')


@app.route('/addexistingmachine')
def add_existing_machine_index():
    ID = str(request.args.get('id'))
    with open('data.json') as file:
        raw_data = json.load(file)
    history = raw_data[0][ID]['issues']
    data = {
        'machine_data': {
            'client_data': raw_data[1][str(raw_data[0][ID]['client_ID'])],
            'machine': raw_data[0][ID]['machine_model'],
            'ID': raw_data[0][ID]['ID']
        },
        'problems_history': history
    }

    return render_template('add_existing_machine.html', data= data)

@app.route('/addexistingmachine', methods=['GET', 'POST'])
def add_existing_machine():
    ID = str(request.args.get('id'))
    with open('data.json') as file:
        new_data = json.load(file)
    problems = request.form.get('problems')
    new_issue = {
        'problems': problems,
        'workforce': {},
        'spare_parts': {},
        'total_price': 0,
        'arrive_date': ctime(), # agrega la fecha en la que se agregó
        'fixing_date': '',
        'delivery_date': ''
    }
    
    new_data[0][ID]['issues'].append(new_issue)
    new_data[0][ID]['status'] = 'Pendiente'
    
    with open('data.json', 'w') as file:
        json.dump(new_data, file, indent=4)
    
    return redirect(f'http://192.168.1.69:5000/machine?id={ID}')


@app.route('/machine', methods=['GET', 'POST'])
def show_machine():
    ID = str(request.args.get('id'))
    with open('data.json') as file:
        raw_data = json.load(file)
    client_ID = str(raw_data[0][ID]['client_ID'])
    machine_data = raw_data[0][ID]
    client_data = raw_data[1][str(raw_data[0][ID]['client_ID'])]
    data = {'m': machine_data['issues'][-1], 'c': client_data, 'a': machine_data}
    if request.method == 'POST':
        service = request.form.get("service")
        service_price = request.form.get("service_price")
        spare_part = request.form.get("spare_part")
        spare_part_price = request.form.get("spare_part_price")
        # agrega repuestos y mano de obra
        if service_price != "" and service_price != None:
            raw_data[0][ID]['issues'][-1]['workforce'][service] = int(service_price)
        if spare_part_price != "" and spare_part_price != None:
            raw_data[0][ID]['issues'][-1]['spare_parts'][spare_part] = int(spare_part_price)
        # cambia el estado a arreglado y calcula el precio total
        if request.form.get('fixed') == 'fixed':
            if raw_data[0][ID]['status'] == 'Pendiente':
                raw_data[0][ID]['status'] = 'Para entregar'
                total_price = 0
                for service, price in raw_data[0][ID]['issues'][-1]['workforce'].items():
                    total_price += price
                for spare_part, price in raw_data[0][ID]['issues'][-1]['spare_parts'].items():
                    total_price += price
                raw_data[0][ID]['issues'][-1]['total_price'] = total_price
                raw_data[0][ID]['issues'][-1]['fixing_date'] = ctime()

                raw_data[1][client_ID]['debt'] += raw_data[0][ID]['issues'][-1]['total_price']

        # cambia el estado a entregada
        if raw_data[0][ID]['status'] == 'Para entregar':
            if request.form.get('delivered') == 'delivered':
                raw_data[0][ID]['status'] = 'Entregada'
                raw_data[0][ID]['issues'][-1]['delivery_date'] = ctime()
                pay = request.form.get('pay')
                raw_data[1][client_ID]['debt'] -= int(pay)
    with open('data.json', 'w') as file:
        json.dump(raw_data, file, indent=4)
        if request.form.get('New issue') == 'New issue':
            return redirect(f'http://192.168.1.69:5000/addexistingmachine?id={ID}')


    return render_template('machines.html', data=data)


def add_machine(client, client_phone, machine_model, problems):
    '''adds a row to the excel file with the data of a machine
    row: 1=client, 2=client_phone, 3=machine, 4=problems'''
    with open('data.json') as file:
        data = json.load(file)
    # crea un nuevo ID de máquina
    ID = int(len(data[0])+101)
    # agrega la máquina al cliente y define el client_ID
    if client in data[2]['clients']:
        for client_data in data[1]:
            if client_data['client'] == client:
                client_ID = data[1]['client_ID']
                data[1][client_ID]['machines'].append(ID)
    # agrega el cliente con la máquina en el caso de que no esté
    else:
        client_ID = len(data[1]) + 101
        client_data = {
            "client_ID": client_ID,
            "client": client,
            "client_phone": client_phone,
            "machines": [ID],
            "debt": 0
        }
        data[1][client_ID] = client_data
        data[2]['clients'].append(client)
    # crea un diccionario con todos los datos para agregarlo al archivo .json
    to_json = {
        'ID': ID,
        'client_ID': client_ID,
        'status': 'Pendiente',
        'machine_model': machine_model,
        'issues': [
            {
                'problems': problems,
                'workforce': {},
                'spare_parts': {},
                'total_price': 0,
                'arrive_date': ctime(), # agrega la fecha en la que se agregó
                'fixing_date': '',
                'deivery_date': ''
            }
        ]
    }
    # en el caso de que la máquina ya haya estado se agrega el problema a la lista
    if ID in data[0]:
        data[0][ID]['issues'].append(to_json['issues'])
        # agrega el elemento al diccionario en forma de [ID] = data
    else:
        data[0][ID] = to_json
    # vuelve a escribir la data actualizada en el archivo .json
    with open('data.json', 'w') as file:
        json.dump(data, file, indent=4)
    # envía la ID al HTML
    return ID

def main(argv):
    app.run(host='192.168.1.69', port=5000, debug=True, threaded=False)

if __name__ == "__main__":
    main(sys.argv)
    
