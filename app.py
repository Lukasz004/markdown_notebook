from flask import Flask, render_template, request, redirect
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user

app = Flask(__name__)
app.secret_key = 'fajny_klucz'

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        return redirect("/main")
    else:
        return render_template('index.html')
    
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        return redirect("/")
    else:
        return render_template('register.html')
    
@app.route("/main", methods=["POST", "GET"])
def main():
    if request.method == "POST":
        pass
    else:
        return render_template("main.html")
    
@app.route('/newnote', methods=["GET", "POST"])
def newnote():
    if request.method == "POST":
        return redirect('/main')
    else:
        return render_template("newnote.html")
    
@app.route('/logout', methods=["GET"])
def logout():
    return redirect('/')
    
if __name__ == "__main__":
    app.run(debug=True)