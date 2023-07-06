from flask_login import current_user


def test_login_wrong_phone(test_client):
    response = test_client.post('/api/auth/login',
                                json={'phone': 79999774706,
                                      'password': 'testicles737'})
    assert current_user.is_anonymous
    assert response.status_code == 401
    assert b"wrong phone number or password" in response.data


def test_login_wrong_pass(test_client):
    response = test_client.post('/api/auth/login',
                                json={'phone': 79999774705,
                                      'password': 'testicles736'})
    assert response.status_code == 401
    assert b"wrong phone number or password" in response.data


def test_login(test_client):
    response = test_client.post('/api/auth/login',
                                json={'phone': 79999774705,
                                      'password': 'testicles737'})
    assert response.status_code == 200


def test_logout(test_client):
    assert not current_user.is_anonymous
    response = test_client.get('/api/auth/logout')
    assert response.status_code == 200
    assert current_user.is_anonymous
