import os
import requests
from flask import Flask, session, render_template, request, url_for, redirect, session, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
@app.route("/signup", methods=["POST", "GET"])
def signup():

    if request.method == "GET":
        return render_template("home.html", title="Home")

    elif request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        username = request.form.get("user_name")
        password = request.form.get("password")
        cpassword = request.form.get("confirm_password")

        if password != cpassword:
            return render_template("home.html", title="Home" ,message="password not matching, Please try again.")

        users = db.execute("SELECT username, email FROM users ").fetchall()

        for user in users:
            if (user.username == username) :
                 return render_template("home.html", title="Home" ,message="username already exist, Please try again.")
            elif (user.email == email):
                return render_template("home.html", title="Home" ,message="email id already exist, Please try again.")

        hash = generate_password_hash(password)

        db.execute("INSERT INTO users(name, username, password, email) VALUES (:name, :username, :password, :email)",
            {"name":name, "username":username, "password":hash, "email":email})
        db.commit()

        session["name"] = name

        return redirect("/login")



@app.route("/login", methods=["POST","GET"])
def login():

    if request.method == 'POST':
        loginid = request.form.get("loginid")
        password = request.form.get("password")

        users = db.execute("SELECT username, email, password FROM users ").fetchall()

        for user in users:
            if ((user.username == loginid or user.email == loginid ) and check_password_hash(user.password, password)):
                session["user"] = loginid
                return redirect('/books')

        return render_template("login.html", title="Log In", message="Username or Password incorrect, Please try again")

    elif request.method == "GET":
        if "name" in session:
            user = session["name"]
            session.pop("name", None)
            return render_template("login.html", title="Log In" ,name=user)
        return render_template("login.html", title="Log In")

@app.route("/books", methods=["POST","GET"])
def books():
    if request.method == "GET":
        if "user" in session:
            return render_template("books.html", title="Books" )
        else:
            return redirect('/login')

    elif request.method == "POST":
        book = request.form.get("name")
        s_parameter = request.form.get("search")

        if s_parameter == "isbn":
            query = f"SELECT title FROM books WHERE isbn ILIKE '%{book}%'"
        elif s_parameter == "title":
            query = f"SELECT title FROM books WHERE title ILIKE '%{book}%'"
        elif s_parameter == "author":
            query = f"SELECT title FROM books WHERE author ILIKE '%{book}%'"
        else:
            query = f"SELECT title FROM books WHERE isbn ILIKE '%{book}%' or title ILIKE '%{book}%' or  author ILIKE '%{book}%'"

        dbbooks = db.execute(query).fetchall()
        msg = "No such book exist"

        if dbbooks:
            return render_template("books.html", title="Books", books=dbbooks)
        else:
            return render_template("books.html", title="Books", books=dbbooks, message=msg)


@app.route("/bookpage/<string:book>", methods=["POST","GET"])
def bookpage(book):
    if request.method == "GET":
        if "user" in session:

            facts = db.execute(f"SELECT * FROM books where title = '{book}'").fetchall()
            review = db.execute(f"SELECT review, rating FROM reviews where book_id = '{facts[0][0]}' ").fetchall()

            return render_template("bookpage.html", title="Books", book=book, facts=facts, review=review)
        else:
            return redirect('/login')

    elif request.method == "POST":
        if "user" in session:
            facts = db.execute(f"SELECT * FROM books WHERE title = '{book}'").fetchall()

            username = session["user"]
            user1 = db.execute(f"SELECT * FROM users WHERE username = '{username}'").fetchall()

            review = request.form.get("review")
            rating = request.form.get("rating")

            rw = db.execute(f"SELECT review, rating FROM reviews WHERE user_id = '{user1[0][0]}' and book_id = '{facts[0][0]}' ").fetchall()


            if len(rw) == 0:
                db.execute("INSERT INTO reviews(user_id, book_id, review, rating) VALUES (:user_id, :book_id, :review, :rating)",
                    {"user_id":user1[0][0], "book_id":facts[0][0],  "review":review, "rating":rating })
                # if review != None:
                #     db.execute(f"UPDATE reviews SET review ='{review}' ")
                # if rating != None:
                #     db.execute(f"UPDATE reviews SET rating = {rating} ")
                db.commit()

                review = db.execute(f"SELECT review, rating FROM reviews WHERE book_id = '{facts[0][0]}' ").fetchall()
                return  render_template("bookpage.html", title="Books", book=book, facts=facts, review=review)

            for items in rw:
                if items.rating != None and items.review != "":
                    msg = "Already rated the book"
                if items.rating == None:
                    db.execute(f"UPDATE reviews SET rating = {rating} WHERE user_id = '{user1[0][0]}' and book_id = '{facts[0][0]}'")
                if items.review == "":
                    db.execute(f"UPDATE reviews SET review = '{review}' WHERE user_id = '{user1[0][0]}' and book_id = '{facts[0][0]}'")
                db.commit()



                review = db.execute(f"SELECT review, rating FROM reviews WHERE book_id = '{facts[0][0]}' ").fetchall()
                return  render_template("bookpage.html", title="Books", book=book, facts=facts, review=review, msg=msg)


@app.route("/api/<string:book_name>")
def book_api(book_name):

    book = db.execute(f"SELECT * FROM books WHERE title = '{book_name}' ").fetchall()
    if len(book) == 0 :
        return jsonify({"error":"Invalid book name"})

    book_review = db.execute(f"SELECT review FROM reviews  WHERE book_id = '{book[0][0]}' ").fetchall()
    book_rating = db.execute(f"SELECT rating FROM reviews WHERE book_id = '{book[0][0]}' ").fetchall()

    totalcount = 0
    totalsum = 0
    for items in book_rating:
        totalsum += items.rating
        totalcount += 1
    avg = totalsum / (totalcount)


    return jsonify({
        "title": book[0][2],
        "author": book[0][3],
        "year": book[0][4],
        "isbn": book[0][1],
        "review_count": len(book_review),
        "average_score": avg
    })

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect('/signup')
