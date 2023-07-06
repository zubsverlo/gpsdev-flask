from flask import g


def test_employees_get(client_authorized):
    request = client_authorized.get('/api/employees/')
    assert request.status_code == 200


def test_employees_post(client_authorized):
    new_employee = {
        "name": "Тест Сотрудник",
        "division": 3,
        "phone": "79999774704"
    }
    request = client_authorized.post('/api/employees/',
                                     json=new_employee)
    new_employee_name_id = request.get_json().get('name_id')

    assert request.status_code == 200
    assert new_employee_name_id
    g.new_employee_name_id = new_employee_name_id


def test_new_employee_name_id_exists(client_authorized):
    assert g.get('new_employee_name_id')


def test_employee_get(client_authorized):
    assert g.get('new_employee_name_id')
    name_id = g.get('new_employee_name_id')
    request = client_authorized.get('/api/employees/'+str(name_id))
    assert request.status_code == 200
    assert request.get_json().get('name_id') == name_id


def test_employee_patch(client_authorized):
    name_id = g.get('new_employee_name_id')
    request = client_authorized.patch(
        '/api/employees/' + str(name_id),
        json={'name': 'Тест Сотрудник (переименован)'}
    )
    assert request.status_code == 200
    assert request.get_json().get('name') == 'Тест Сотрудник (переименован)'


def test_employee_delete(client_authorized):
    name_id = g.get('new_employee_name_id')
    request = client_authorized.delete('/api/employees/'+str(name_id))
    assert request.status_code == 200



