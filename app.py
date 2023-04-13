# CONCENTRAÇÃO DO PROGRAMA EM APENAS UM ARQUIVO (NÃO RECOMENDADO)
# SEM AMBIENTE VIRTUAL

# pip install mysql-connector-python

# CRIAÇÃO DE BASE DE DADOS PADRÃO
# DIRETO DO CONFIG.PY

'''
CREATE DATABASE flask_app;
USE flask_app;
CREATE TABLE users (
  id INT(11) NOT NULL AUTO_INCREMENT,
  username VARCHAR(50) NOT NULL,
  password VARCHAR(255) NOT NULL,
  is_admin BOOLEAN NOT NULL DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY username (username)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
'''
'''
# config.py
MYSQL_DATABASE_USER = 'user'
MYSQL_DATABASE_PASSWORD = 'password'
MYSQL_DATABASE_DB = 'flask_app'
MYSQL_DATABASE_HOST = 'localhost'
'''

# app.py

# PRINCIPAL COM IMPORTS ANTIGOS (ANOTAR PARA NÃO ESQUECER)
# IMPORTS ATUAIS E PROGRAMA PRINCIPAL

from forsearch import searchreq
import json
import requests
from datetime import timedelta
import argparse
from newsapi import NewsApiClient
import requests
import string
from flask import Flask, render_template, redirect, request, url_for, session, flash
from werkzeug.security import generate_password_hash
from mysql.connector import connect
from config import *

# PRINCIPAL PARTE DO PROGRAMA (FLASK)

app = Flask(__name__)
app.config.from_pyfile('config.py')
app.secret_key = 'secret'

# MODELO DE USO PARA BASE DE DADOS

def connect_to_database():
    return connect(
        user=app.config['MYSQL_DATABASE_USER'],
        password=app.config['MYSQL_DATABASE_PASSWORD'],
        host=app.config['MYSQL_DATABASE_HOST'],
        database=app.config['MYSQL_DATABASE_DB'],
        charset='utf8mb4',
        collation='utf8mb4_unicode_ci'
    )

# ROSTO DO PROJETO E GERENCIAMENTO DE LOGIN, SIGNUP E LOGOUT

# PÁGINA INICIAL (ROSTO)

@app.route('/')
def index():
    return render_template('index.html')

# LOGIN

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = connect_to_database()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password))
        user = cursor.fetchone()
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['is_admin'] = user[3]
            return redirect(url_for('admin' if user[3] else 'user'))
        else:
            return render_template('login.html', error='Utilizador ou senha inválidos!')
    else:
        return render_template('login.html')

# SIGNUP

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin_pass = request.form['admin_pass']
        db = connect_to_database()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password))
        user = cursor.fetchone()

        if user: # if a user is found, we want to redirect back to signup page so user can try again  
            return render_template('signup.html', error='Utilizador já existe!')
        else:
            admin_bool = False

            if admin_pass == 'quemtemasenha':
                admin_bool = True


            cursor.execute('INSERT INTO users VALUES (default, %s, %s, %s)', (username, password, admin_bool))
            db.commit()
            cursor.close()
            return redirect(url_for('login', success='Utilizador criado com sucesso!'))
    else:
        return render_template('signup.html')

#LOGOUT

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('is_admin', None)
    return redirect(url_for('index'))

# VERIFICAÇÃO SE UTILIZADOR É ADMIN PARA ENTÃO FAZER O LOGIN DE FORMA CORRETA

@app.route('/admin')
def admin():
    if 'user_id' in session and session['is_admin']:
        db = connect_to_database()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM users')
        users = cursor.fetchall()
        return render_template('admin.html', users=users)
    else:
        return redirect(url_for('login'))

# PARTE PRINCIPAL DO CRUD (ACESSO APENAS PELO ADMIN)

# INSERIR NOVO UTILIZADOR

@app.route('/insert', methods = ['POST'])
def insert():

    if request.method == "POST":
        flash("Dados Inseridos com Sucesso")
        username = request.form['username']
        password = request.form['password']
        admin = True
        try:
            admin = request.form['admin']
        except:
            admin = False

        db = connect_to_database()
        cur = db.cursor()
        cur.execute("INSERT INTO users VALUES (default, %s, %s, %s)", (username, password, admin))
        db.commit()
        return redirect(url_for('admin'))

# DELETAR UTILIZADOR 

@app.route('/delete/<string:id_data>', methods = ['GET'])
def delete(id_data):
    flash("Registro apagado com sucesso!")
    db = connect_to_database()
    cur = db.cursor()
    cur.execute("DELETE FROM users WHERE id=%s", (id_data,))
    db.commit()
    return redirect(url_for('admin'))

# UPDATE DE UTILIZADOR JÁ EXISTENTE

@app.route('/update',methods=['POST','GET'])
def update():
    if request.method == 'POST':
        id_data = request.form['id']
        username = request.form['username']
        password = request.form['password']
        admin = True
        try:
            admin = request.form['admin']
        except:
            admin = False

        db = connect_to_database()
        cur = db.cursor()
        cur.execute("""
               UPDATE users
               SET username=%s, password=%s, is_admin=%s
               WHERE id=%s
            """, (username, password, admin, id_data))
        flash("Dados atualizados com sucesso!")
        db.commit()
        return redirect(url_for('admin'))

# ACESSO DO UTILIZADOR COMUM (SEM GRANDES INFORMAÇÕES)
# VÊ APENAS SUAS PRÓPRIA INFORMAÇÕES

@app.route('/user')
def user():
    if 'user_id' in session:
        db = connect_to_database()
        cursor = db.cursor()
        cursor.execute(f"SELECT * FROM users WHERE id = {session['user_id']}")                                                                                  
        users = cursor.fetchall()
        return render_template('user.html', users=users)
    else:
        return redirect(url_for('login'))

# INÍCIO DA PARTE DO CLIMA (USO DE API)

weather_data = []

# PESQUISA/GERA INFORMAÇÃO DA CIDADE PESQUISADA

@app.route('/weather', methods=['POST', 'GET'])
def weather():
    if request.method == 'POST':
        err_msg = ''
        new_city = request.form.get('city')
        new_city = new_city.lower()
        new_city = string.capwords(new_city)

        url = f"http://api.openweathermap.org/data/2.5/weather?q={new_city}&lang=PT&units=metric&appid=b21a2633ddaac750a77524f91fe104e7"
        r = requests.get(url).json()

        if r['cod'] == 200:
            weather = {
                'city' : r['name'],
                'temperature' : r['main']['temp'],
                'description' : r['weather'][0]['description'],
                'icon' : r['weather'][0]['icon'],
            }
            weather_data.append(weather)

            return render_template('weather.html', weather_data=weather_data, success=f"Cidade adicionada com sucesso!") 
        else:
            return render_template('weather.html', weather_data=weather_data, error='Esta cidade não existe!')
    return render_template('weather.html', weather_data=weather_data)

# DELETA CIDADE PELO NOME

@app.route('/deletecity/<name>')
def delete_city( name ):
    for i in range(len(weather_data)):    
        if weather_data[i]['city'] == name:
            del weather_data[i]
            break
    return render_template('weather.html', weather_data=weather_data, error=f'Cidade {name} deletada com sucesso!')

# INÍCIO DA PARTE DE NOTÍCIAS (API)
# "BASE DE DADOS" DE API-KEYS DO NEWSAPI.ORG
# NEWSAPI.ORG TEM APENAS 50 REQUESTS A CADA 12H

#newsapi = NewsApiClient(api_key='64c7d8c3157f4105bff944ccb2eb7793')
#newsapi = NewsApiClient(api_key='b1fba6c8a4eb4f7bb2833ae155ccd681')
newsapi = NewsApiClient(api_key='10e0a5fb283c488b8489b7dbebcd324f')
#newsapi = NewsApiClient(api_key='ae08d7c1d12047eca402fd5704f46e72')

# CONFIGURAÇÃO PRINCIPAL DE ACESSO AOS SITES QUE BUSCAM NOTÍCIAS

def get_sources_and_domains():
	all_sources = newsapi.get_sources()['sources']
	sources = []
	domains = []
	for e in all_sources:
		id = e['id']
		domain = e['url'].replace("http://", "")
		domain = domain.replace("https://", "")
		domain = domain.replace("www.", "")
		slash = domain.find('/')
		if slash != -1:
			domain = domain[:slash]
		sources.append(id)
		domains.append(domain)
	sources = ", ".join(sources)
	domains = ", ".join(domains)
	return sources, domains

# BUSCA PRINCIPAL DAS NOTÍCIAS DE ACORDO COM PEQUENAS CONFIGURAÇÕES
# USAR COUNTRY "US" E LANGUAGE "EN" PARA CARREGAR AUTOMATICAMENTE
# FUNCIONA COM "PT" MAS NÃO GERA INFORMAÇÕES AO CARREGAR A PÁGINA (NECESSÁRIO PESQUISAR)

@app.route("/news", methods=['GET', 'POST'])
def home():
	if request.method == "POST":
		sources, domains = get_sources_and_domains()
		keyword = request.form["keyword"]
		related_news = newsapi.get_everything(q=keyword,
									sources=sources,
									domains=domains,
									language='en',
									sort_by='relevancy')
		no_of_articles = related_news['totalResults']
		if no_of_articles > 100:
			no_of_articles = 100
		all_articles = newsapi.get_everything(q=keyword,
									sources=sources,
									domains=domains,
									language='en',
									sort_by='relevancy',
									page_size = no_of_articles)['articles']
		return render_template("home.html", all_articles = all_articles,
							keyword=keyword)
	else:
		top_headlines = newsapi.get_top_headlines(country="us", language="en")
		total_results = top_headlines['totalResults']
		if total_results > 100:
			total_results = 100
		all_headlines = newsapi.get_top_headlines(country="us",
													language="en",
													page_size=total_results)['articles']
		return render_template("home.html", all_headlines = all_headlines)
	return render_template("home.html")

# INÍCIO DA PARTE DE FILMES (API)
# PESQUISA NO IMDB PELAS INFORMAÇÕES DO FILME E USA O FORSEARCH.PY PARA BUSCAR 
# OS CARTAZES DOS FILMES DE OUTRA API

app.config["SESSION_PERMANENT"]=True

app.config["PERMANENT_SESSION_LIFETIME"]=timedelta(days=31)

app.secret_key="d273fd202ae36a79dd36f160616859903861e535d49b44793b1d2930b05ff33a"

# RENDERIZA A PÁGINA PRINCIPAL (VAZIA)

@app.route('/movie')
def index2():
	return render_template('index2.html')

# MEDIANTE PESQUISA BUSCA POR FILMES, SÉRIES E OUTROS NO IMDB

@app.route('/search', methods=['POST'])
def search():
	"""if POST, query movie api for data and return results."""
	title=request.form['title']
	try:
		jsonresp=searchreq(title)
		results=jsonresp["Search"]
		return render_template("search_results.html",results=results)
	except Exception as e:
		return render_template("notfound.html"),404

# GERENCIADOR DE ERRO CASO NÃO SEJA ENCONTRADO O QUE FOI DIGITADO NA PESQUISA

@app.errorhandler(404)
def notfound(error):
	return render_template('notfound.html'),404

# PARA MANTER PÁGINA EM FUNCIONAMENTO (CORRENDO)

if __name__ == '__main__':
    app.run(debug=True)
