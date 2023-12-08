from flask import render_template, url_for, redirect, jsonify
from flask_login import login_required, current_user
from flask.blueprints import Blueprint
import json


pages = Blueprint('/pages', __name__)


@pages.route('/login')
def login():
    if not current_user.is_anonymous:
        if current_user.rang_id != 1:
            return redirect(url_for('/pages.attends'))
        return redirect(url_for('/pages.dashboard'))
    return render_template('login.html')


@pages.route('/')
@login_required
def home():
    if current_user.rang_id != 1:
        return redirect(url_for('/pages.attends'))
    return redirect(url_for('/pages.dashboard'))


@pages.route('/attends')
@login_required
def attends():
    return render_template('attends.html', title='Посещения')


@pages.route('/objects')
@login_required
def objects():
    return render_template('objects.html', title='Подопечные')


@pages.route('/employees')
@login_required
def employees():
    return render_template('employees.html', title='Сотрудники')


@pages.route('/journal')
@login_required
def journal():
    return render_template('journal.html', title='Журнал')


@pages.route('/users')
@login_required
def users():
    return render_template('users.html', title='Пользователи')


@pages.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', title='Dashboard')


@pages.route('/swagger.json')
def swagger():
    with open('openapi.json', 'r') as f:
        return jsonify(json.load(f))
