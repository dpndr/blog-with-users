from datetime import date, timedelta
from flask import Flask, abort, render_template, redirect, url_for, flash, request, session
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
import os
from dotenv import load_dotenv
import smtplib

load_dotenv(".env")
year = date.today().year

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("FLASK_KEY")
ckeditor = CKEditor(app)
Bootstrap5(app)
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)
# TODO: Configure Flask-Login

login_manager = LoginManager()
login_manager.init_app(app)


# CREATE DATABASE
class Base(DeclarativeBase):
    pass


app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DB_URI", "sqlite:///posts.db")
db = SQLAlchemy(model_class=Base)
db.init_app(app)


# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    author = relationship("User", back_populates="posts")
    author_id: Mapped[int] = mapped_column(db.ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    comments = relationship("Comments", back_populates="parent_post")


# TODO: Create a User table for all your registered users.
class User(db.Model, UserMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str]
    name: Mapped[str]
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comments", back_populates="c_author")


class Comments(db.Model):

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str]
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    c_author = relationship("User", back_populates="comments")
    post_id: Mapped[int] = mapped_column(ForeignKey("blog_posts.id"))
    parent_post = relationship("BlogPost", back_populates="comments")


with app.app_context():
    db.create_all()


def admin_only(fn):
    @wraps(fn)
    def decorated_fn(*args, **kwargs):
        if current_user.id == 1:
            return fn(*args, **kwargs)
        else:
            return abort(403)

    return decorated_fn


def author_only(fn):
    @wraps(fn)
    def decorated_fn(*args, **kwargs):
        author_id = int(kwargs.get("author_id"))
        if current_user.id == author_id or current_user.id == 1:
            return fn(*args, **kwargs)
        else:
            return abort(403)
    return decorated_fn


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    return db.get_or_404(User, user_id)


# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register', methods=["POST", "GET"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data
        user = db.session.execute(db.select(User).where(User.email == email)).scalar()
        if user:
            flash("You've already signed up with that email, log in instead")
            return redirect(url_for('login'))
        hashed_and_salted_password = generate_password_hash(form.password.data, method="pbkdf2:sha256:600000",
                                                            salt_length=8)
        # noinspection PyArgumentList
        new_user = User(
            name=form.name.data,
            email=form.email.data,
            password=hashed_and_salted_password
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        if form.logged_in.data:
            session.permanent = True
            session["user_id"] = user.id
        else:
            session.permanent = False
        return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form, year=year)


# TODO: Retrieve a user from the database based on their email. 
@app.route('/login', methods=["POST", "GET"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        user = db.session.execute(db.select(User).where(User.email == email)).scalar()
        if not user:
            flash('That email does not exist. Please try again.')
        elif not check_password_hash(user.password, form.password.data):
            flash('Invalid password, please try again.')
        else:

            if form.logged_in.data:
                login_user(user, remember=True)
            else:
                login_user(user)

            return redirect(url_for("get_all_posts"))
    return render_template("login.html", form=form, year=year)


@app.route('/logout')
def logout():
    logout_user()
    session.pop("user_id", None)
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts, current_user=current_user, year=year)


# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>", methods=["POST", "GET"])
def show_post(post_id):
    requested_post = db.get_or_404(BlogPost, post_id)
    form = CommentForm()
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))
        new_comment = Comments(
            text=form.comment.data,
            c_author=current_user,
            parent_post=requested_post
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for("show_post", post_id=requested_post.id) + '#comment_form')
    return render_template("post.html", post=requested_post, current_user=current_user,
                           form=form, year=year)


# TODO: Use a decorator so only an admin user can create a new post
@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, year=year)


# TODO: Use a decorator so only an admin user can edit a post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True, year=year)


# TODO: Use a decorator so only an admin user can delete a post
@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/deleteComment/<post_id>/<comment_id>/<author_id>")
@author_only
def delete_comment(post_id, comment_id, author_id):
    comment_to_delete = db.get_or_404(Comments, comment_id)
    db.session.delete(comment_to_delete)
    db.session.commit()
    return redirect(url_for('show_post', post_id=post_id) + '#comment_form')


# @app.route("/editComment/<post_id><comment_id><author_id>")
# @author_only
# def edit_comment(post_id, comment_id, author_id):
#     comment_to_edit = db.get_or_404(Comments, comment_id)
#
#     db.session.commit()
#     return redirect(url_for('show_post', post_id=post_id))


@app.route("/about")
def about():
    return render_template("about.html", year=year)


@app.route("/contact", methods=['GET', 'POST'])
def contact():
    if request.method == 'GET':
        return render_template("contact.html", year=year, header='Contact Me')
    if request.method == 'POST':
        with smtplib.SMTP("smtp.gmail.com", port=587) as connection:
            connection.starttls()
            connection.login(user=os.getenv("EMAIL"), password=os.getenv("PASSWORD"))
            connection.sendmail(from_addr=os.getenv("EMAIL"),
                                to_addrs=os.getenv("EMAIL"),
                                msg=f"Subject:New Message \n\nName: {request.form['name']}\nEmail: {request.form['email']}\n"
                                    f"Phone: {request.form['phone']}\nMessage: {request.form['message']}")
        return render_template("contact.html", year=year, header='Successfully sent your message')


if __name__ == "__main__":
    app.run(debug=False)
