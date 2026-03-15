from flask import Flask, render_template, request, redirect, url_for, flash, get_flashed_messages
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import sqlite3
import markdown
import bleach
import re
import time
import pyotp
import qrcode
import os
from base64 import b64encode, b64decode
from io import BytesIO
from uuid import uuid4
from argon2 import PasswordHasher
from secrets import token_urlsafe
from Crypto.Cipher import AES
from Crypto.Hash import SHA256

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

pepper = os.getenv('PEPPER')

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://"
)

DATABASE = os.getenv('DATABASE')

class User(UserMixin):
    def __init__(self, login, password, id):
        self.login = login
        self.password = password
        self.id = id

@login_manager.user_loader
def user_loader(userid):
    try:
        db = sqlite3.connect(DATABASE)
        sql = db.cursor()
        sql.execute('SELECT login, password, id FROM users WHERE id=(?)', (userid,))
        row = sql.fetchone()
        if row:
            login, password, id = row
            return User(login, password, id)
        else:
            return None
    except Exception as e:
        db.rollback()
    finally:
        db.close()

@app.route("/", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if request.method == "POST":
        login = request.form['login']
        password = request.form['password']
        totpcode = request.form['2fa']
        error = False

        if not login:
            flash('Wprowadź login!', 'error')
            error = True
        if not password:
            flash('Wprowadź hasło!', 'error')
            error = True

        if not error:
            ph = PasswordHasher()
            defaultRow = ('$argon2id$v=19$m=65536,t=3,p=4$tFF7XGiar68rH6iXzo5T4g$7lPmJ6dFh0wdb+9DgG+KXz7Vf0OtWWXS1rCvETWHPsk', 
                          '4691e982-abbd-4728-9ba1-e9cc63d98c09', 
                          'snr8KWYOGGhFbb+E6ckz+JWkI0dqxrQGGb12J9pkGJE=', 
                          'RXIQHpEjCRX84QfnKjboig==')   #data for password test and login test (this will not pass password validation in register so noone can use that)
            try:
                db = sqlite3.connect(DATABASE)
                sql = db.cursor()
                sql.execute('SELECT password, id, totpsecret, totpiv FROM users WHERE login=(?)', (login,))
                row = sql.fetchone()
                try:       
                    dbpassword, id, encryptedSecret, IV = row
                    totpsecret = decryptSecret(password, encryptedSecret, IV)
                except:
                    row = defaultRow
                    password = 'test'
                    dbpassword, id, encryptedSecret, IV = row
                    totpsecret = decryptSecret(password, encryptedSecret, IV)
                
                totp = pyotp.TOTP(totpsecret)
                user = User(login, dbpassword, id)
                if ph.verify(user.password, password+pepper) and totp.verify(totpcode):
                    login_user(user)
                    return redirect(url_for('main'))
                else:
                    flash('Wprowadzone dane nie są poprawne!', 'error')
            except:
                db.rollback()
            finally:
                db.close()

        return redirect(url_for('login'))
    else:
        return render_template('index.html')
    
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        login = request.form['login']
        password = request.form['password']
        retypedPassword = request.form['retype-password']
        error = False

        if not login:
            flash('Nie podano loginu!', 'error')
            error = True
        if not password:
            flash('Nie podano hasła!', 'error')
            error = True
        if password != retypedPassword:
            flash('Hasła się nie zgadzają!', 'error')
            error = True
        if not error and (not re.fullmatch(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{10,}$', password)):
            flash('Wprowadzone hasło nie spełnia wymagań. Powinno posiadać małą literę, dużą i cyfrę oraz mieć co najmniej 10 znaków', 'error')
            error = True

        ph = PasswordHasher()
        hashedPassword = ph.hash(password+pepper)
        if not error:
            secret, b64qr = initTOTP(login)
            encryptedSecret, IV = encryptSecret(password, secret)
            try:
                db = sqlite3.connect(DATABASE)
                sql = db.cursor()
                sql.execute('INSERT INTO users(login, password, id, totpsecret, totpiv) VALUES (?,?,?,?,?)', (login, hashedPassword, str(uuid4()), encryptedSecret, IV))
                db.commit()
                flash('Utworzono konto! Teraz dodaj 2fa', 'success')
                return render_template('2fa.html', qrcode=b64qr)
            except sqlite3.IntegrityError:
                flash('Podany login już istnieje!', 'error')
                db.rollback()
            finally:
                db.close()
        
        return redirect(url_for('register'))

    else:
        return render_template('register.html')
    
def initTOTP(login):
    secret = pyotp.random_base32()
    totp = pyotp.totp.TOTP(secret).provisioning_uri(
        name=login,
        issuer_name='Najlepsze notatki'
    )
    buffer = BytesIO()
    qrcode.make(totp).save(buffer, format="PNG")
    b64qr = b64encode(buffer.getvalue()).decode('utf-8')
    return secret, b64qr

def encryptSecret(password, secret):
    h = SHA256.new()
    h.update(password.encode('utf-8'))
    cipher = AES.new(h.digest(), AES.MODE_CBC)
    IV = b64encode(cipher.iv).decode('utf-8')
    cipherSecret = b64encode(cipher.encrypt(secret.encode('utf-8'))).decode('utf-8')

    return cipherSecret, IV

def decryptSecret(password, cipherSecret, IV):
    h = SHA256.new()
    h.update(password.encode('utf-8'))
    print('test de1')
    cipher = AES.new(h.digest(), AES.MODE_CBC, iv=b64decode(IV))
    print('test de2')
    secret = cipher.decrypt(b64decode(cipherSecret)).decode('utf-8')
    print('test de3')


    return secret


@app.route("/main", methods=["POST", "GET"])
@login_required
def main():
    if request.method == "POST":
        pass
    else:
        notes = getnotes()
        return render_template("main.html", notes=notes)
    
def getnotes():
    try:
        db = sqlite3.connect(DATABASE)
        sql = db.cursor()
        sql.execute('SELECT id, note, title FROM notes WHERE owner=(?)', (current_user.login,))
        rows = sql.fetchall()
        sanitizedRows = []
        for id, note, title in rows:
            note = sanitizeMarkdown(note)
            title = sanitizeTitle(title)
            sanitizedRows.append((id, note, title))
        return sanitizedRows
    except:
        db.rollback()
        return None
    finally:
        db.close()
    
@app.route('/newnote', methods=["GET", "POST"])
@login_required
def newnote():
    if request.method == "POST":
        note = request.form['note']
        title = request.form['title-input']
        error = False

        if not note:
            flash("Nie można dodać pustej notatki!", 'error')
            error = True
        elif not title:
            flash("Notatka musi mieć tytuł!", 'error')
            error = True

        if not error:
            try:
                db = sqlite3.connect(DATABASE)
                sql = db.cursor()
                sql.execute('INSERT INTO notes (id, note, title, owner) VALUES (?,?,?,?)', (str(uuid4()), note, title, current_user.login))
                db.commit()
                return redirect(url_for('main'))
            except Exception as e:
                print(e)
                db.rollback()
                flash('Błąd w dodawaniu notatki!', 'error')
            finally:
                db.close()
        
        return redirect(url_for('newnote'))
        
    else:
        return render_template("newnote.html")
    
def sanitizeMarkdown(text):
    tags = {'p','h1','h2','h3','h4','h5','h6', 'blackquote', 'ul', 'ol', 'li', 'pre', 'hr', 'em', 'strong', 'code', 'a', 'img', 'br'}
    attribs = ['href', 'title', 'alt', 'class']
    md = markdown.markdown(text)
    clean_md = bleach.clean(md,tags=tags, attributes=attribs)
    return clean_md

def sanitizeTitle(text):
    tags = {}
    attribs = []
    clean_title = bleach.clean(text, tags=tags, attributes=attribs, strip=True)
    return clean_title

@app.route('/delete', methods=["POST"])
@login_required
def delete():
    id = request.get_json().get('id')

    try:
        db = sqlite3.connect(DATABASE)
        sql = db.cursor()
        sql.execute('DELETE FROM notes WHERE id=(?) AND owner=(?)', (id, current_user.login))
        db.commit()
    except:
        db.rollback()
        return 'Nie można usunąć wiadomosci', 500
    finally:
        db.close()
    
    return "Wiadomosc usunieta pomyslnie", 200

@app.route('/logout', methods=["GET"])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))
    
if not os.path.exists(DATABASE):
    print('Initializing database...')
    db = sqlite3.connect(DATABASE)
    sql = db.cursor()
    sql.execute('DROP TABLE IF EXISTS users')
    sql.execute('CREATE TABLE users(id TEXT PRIMARY KEY NOT NULL, login TEXT NOT NULL UNIQUE, password TEXT NOT NULL, totpsecret TEXT NOT NULL, totpiv TEXT NOT NULL)')
    sql.execute('DROP TABLE IF EXISTS notes')
    sql.execute('CREATE TABLE notes(id TEXT PRIMARY KEY NOT NULL, note TEXT NOT NULL, title TEXT NOT NULL UNIQUE, owner TEXT NOT NULL)')
    db.commit()
