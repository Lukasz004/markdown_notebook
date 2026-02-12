from flask import Flask, render_template, request, redirect, url_for, flash, get_flashed_messages
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
import sqlite3
import markdown
import bleach
import re
from uuid import uuid4
from argon2 import PasswordHasher

app = Flask(__name__)
app.secret_key = 'fajny_klucz'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

DATABASE = './database.db'

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
def login():
    if request.method == "POST":
        login = request.form['login']
        password = request.form['password']
        error = False

        if not login:
            flash('Wprowadź login!', 'error')
            error = True
        if not password:
            flash('Wprowadź hasło!', 'error')
            error = True

        if not error:
            ph = PasswordHasher()
            try:
                db = sqlite3.connect(DATABASE)
                sql = db.cursor()
                sql.execute('SELECT password, id FROM users WHERE login=(?)', (login,))
                row = sql.fetchone()
                if row:
                    dbpassword, id = row
                    user = User(login, dbpassword, id)
                    if ph.verify(user.password, password):
                        login_user(user)
                        return redirect(url_for('main'))
                    else:
                        flash('Wprowadzone dane nie są poprawne!', 'error')
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
        hashedPassword = ph.hash(password)
        if not error:
            try:
                db = sqlite3.connect(DATABASE)
                sql = db.cursor()
                sql.execute('INSERT INTO users(login, password, id) VALUES (?,?,?)', (login, hashedPassword, str(uuid4())))
                db.commit()
                flash('Utworzono konto!', 'success')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash('Podany login już istnieje!', 'error')
                db.rollback()
            finally:
                db.close()
        
        return redirect(url_for('register'))

    else:
        return render_template('register.html')
    
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
        return rows
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
            note = sanitizeMarkdown(note)
            title = sanitizeTitle(title)
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
    
if __name__ == "__main__":
    print('Initializing database...')
    db = sqlite3.connect(DATABASE)
    sql = db.cursor()
    sql.execute('DROP TABLE IF EXISTS users')
    sql.execute('CREATE TABLE users(id TEXT PRIMARY KEY NOT NULL, login TEXT NOT NULL UNIQUE, password TEXT NOT NULL)')
    sql.execute('DROP TABLE IF EXISTS notes')
    sql.execute('CREATE TABLE notes(id TEXT PRIMARY KEY NOT NULL, note TEXT NOT NULL, title TEXT NOT NULL UNIQUE, owner TEXT NOT NULL)')
    db.commit()

    app.run(debug=True)