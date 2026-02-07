from flask import Flask, render_template, request, redirect, url_for, flash, get_flashed_messages
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
import sqlite3
from uuid import uuid4

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
            try:
                db = sqlite3.connect(DATABASE)
                sql = db.cursor()
                sql.execute('SELECT password, id FROM users WHERE login=(?)', (login,))
                row = sql.fetchone()
                if row:
                    dbpassword, id = row
                    user = User(login, dbpassword, id)
                    if user.password == password:
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

        if not error:
            try:
                db = sqlite3.connect(DATABASE)
                sql = db.cursor()
                sql.execute('INSERT INTO users(login, password, id) VALUES (?,?,?)', (login, password, str(uuid4())))
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
        return render_template("main.html")
    
@app.route('/newnote', methods=["GET", "POST"])
@login_required
def newnote():
    if request.method == "POST":
        return redirect('/main')
    else:
        return render_template("newnote.html")
    
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
    db.commit()

    app.run(debug=True)