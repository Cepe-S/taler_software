import csv
import json
import os
import re
import sys
from time import ctime

import flask
from flask import Flask, render_template, request
from flask.helpers import url_for
from werkzeug.utils import redirect

os.chdir(os.path.dirname(__file__))

app = Flask(__name__)

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
def new_machine():
    client = request.form['client']
    client_phone = request.form['client_phone']
    machine_model = request.form['machine_model']
    problems = request.form['problems']
    ID = add_machine(client, client_phone, machine_model, problems)
    data = f'Máquina agregada con ID = {ID}'
    return render_template('add_machine.html', data= data)


@app.route('/machine', methods=['GET', 'POST'])
def show_machine():
#    if request.method == 'GET':
        id = str(request.args.get('id'))
        
#    if request.method == 'POST':
        with open('data.json') as file:
            raw_data = json.load(file)
            try:
                page = int(request.args.get('page'))
            except:
                page = len(raw_data[0][id]) - 1
            data = raw_data[0][id][page]
        ID = str(request.args.get('id'))

        service = request.form.get("service", False)
        service_price = request.form.get("service_price", False)
        spare_part = request.form.get("spare_part", False)
        spare_part_price = request.form.get("spare_part_price", False)

        if service_price != "":
            raw_data[0][ID][-1]['workforce'][service] = int(service_price)
        if spare_part != "false ":
            raw_data[0][ID][-1]['spare_parts'][spare_part] = spare_part_price

        with open('data.json', 'w') as file:
            json.dump(raw_data, file, indent=4)

        return render_template('machines.html', data=data)



def add_machine(client, client_phone, machine_model, problems):
    '''adds a row to the excel file with the data of a machine
    row: 1=ID, 2=client, 3=client_phone, 4=machine, 5=problems, 6=status'''
    with open('data.json') as file:
        data = json.load(file)
    # TODO: agregar else/if statement para evitar agregar problemas a maquinas no arregladas
    # crea un nuevo ID de máquina
    ID = int(len(data[0])+101)
    # TODO: agregar diccionario con contactos y nombres para no tener que introducir número de teléfono
    # crea un diccionario con todos los datos para agregarlo al archivo .json
    to_json = {
        'ID': ID,
        'client': client,
        'client_phone': client_phone,
        'machine_model': machine_model,
        'problems': problems,
        'status': 'en espera',
        'workforce': {},
        'spare_parts': {},
        'total_price': 0,
        'arrive_date': ctime(), # agrega la fecha en la que se agregó
        'fixing_date': ''
    }
    # pide confirmación para continuar
    # abre la data anterior
    machines_dict = data[0]
    # en el caso de que la máquina ya haya estado se agrega el problema a la lista
    if ID in machines_dict:
        machines_dict[ID].append(to_json)
        # agrega el elemento al diccionario en forma de [ID] = data
    else:
        machines_dict[ID] = [to_json]
    # vuelve a escribir la data actualizada en el archivo .json
    with open('data.json', 'w') as file:
        json.dump([machines_dict], file, indent=4)
    return ID

def change_status(data):
    machine_id = input('ID de máquina: ')
    machine_index = len(data[0][machine_id]) - 1
    machine_data = data[0][machine_id][machine_index]
    print(f'\nCliente: {machine_data["client"]}\nMáquina: {machine_data["machine_model"]}')
    status = int(input('[1] Para entregar\n[2] Entregada\n:'))
    # cambia el estado a para entregar y agrega los datos para la entrega
    if status == 1:
        # cambia el estado a 'Para entregar'
        machine_data['status'] = 'Para entregar'
        # agrega los arreglos que se hicieron en forma de lista
        fixes = input('Arreglos realizados:\n*separados por una coma*')
        machine_data['fixes'] = fixes.split(',')
        # agrega el precio de la mano de obra
        workforce = int(input('Mano de obra: '))
        machine_data['workforce'] = workforce
        spare_parts = input('Repuestos en formato: respuesto precio, repuesto precio: ')
        total_price = workforce
        # separa el nombre del repuesto del precio
        for part in spare_parts.split(','):
            price = int(((re.search(r' (\d+)$', part)).group())[1:])
            item = part[:-len(str(price))]
            total_price += price
            # agrega el precio y el repuesto en forma de diccionario
            machine_data['spare_parts'][item] = price
        # escribe el precio total
        machine_data['total_price'] = total_price
        confirm = input('\nAplicar cambios?\nEnter = Aplicar\nn = Cancelar')
        if confirm == '':
            machine_data['fixing_date'] = ctime() # agrega la fecha en la que se arregló
            machines_dict = data[0]
            # borra la data vieja y escribe la actualizada
            del machines_dict[machine_id][machine_index]
            machines_dict[machine_id].append(machine_data)
            # vuelve a escribir la data actualizada en el archivo .json
            with open('data.json', 'w') as file:
                json.dump([machines_dict], file, indent=4)
            print(f'Estado cambiado con éxito\nCliente: {machine_data["client"]}')
        else:
            print('Operación cancelada')
        if status == 2:
            # si la máquina no fue arreglada se pregunta si desea continuar
            if machine_data['status'] == 'en espera':
                print('Esta máquina no se registro como arreglada, desea continuar igual?')
                confirm1 = input('Enter = Continuar\nn = Cancelar')
                if confirm1 != '':
                    print('Operación cancelada')
                    return
            # cambia el estado de la máquina a entregada
            machine_data['status'] = 'Entregada'
            # muestra el total a pagar
            print(f'El total a pagar es de: {machine_data["total_price"]}\n')
            # muestra todos los arreglos realizados
            print('Arreglos realizados:')
            for a in machine_data['fixes']:
                print(a)
            # muestra todos los repuestos utilizados
            print(f'Repuestos utilizados:')
            for key in machine_data["spare_parts"]:
                print(f'Repuesto: {key} || Precio: ${machine_data["spare_parts"][key]}')
            # muestra el precio de la mano de obra
            print(f'\nMano de obra: \n${machine_data["workforce"]}')
            # agrega el dinero pagado
            paid = input('Dinero depositado: ')
            machine_data['paid'] = paid
            confirm2 = input('\nAplicar cambios?\nEnter = Aplicar\nn = Cancelar')
            if confirm2 == 'n':
                return
            # agrega la fecha de entrega
            machine_data['delivery_date'] = ctime()
            # extrae la data anterior y los actualiza
            machines_dict = data[0]
            del machines_dict[machine_id][machine_index]
            machines_dict[machine_id].append(machine_data)
            # vuelve a escribir la data actualizada en el archivo .json
            with open('data.json', 'w') as file:
                json.dump([machines_dict], file, indent=4)


def main(argv):
    app.run(host='192.168.1.69', port=5000, debug=True, threaded=False)

if __name__ == "__main__":
    main(sys.argv)
    
