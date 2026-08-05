import os
from datetime import datetime
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
database_url = os.environ.get("DATABASE_URL", "sqlite:///ylohann.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(25), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    bio = db.Column(db.String(180), default="Bienvenue sur Ylohann !")
    avatar = db.Column(db.String(255), default="https://api.dicebear.com/8.x/initials/svg?seed=Ylohann")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user = db.relationship("User", backref="posts")
    comments = db.relationship("Comment", backref="post", cascade="all, delete-orphan")
    likes = db.relationship("Like", backref="post", cascade="all, delete-orphan")


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    user = db.relationship("User")


class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    __table_args__ = (db.UniqueConstraint("user_id", "post_id", name="unique_like"),)


class Friendship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    addressee_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    status = db.Column(db.String(15), default="pending")
    requester = db.relationship("User", foreign_keys=[requester_id])
    addressee = db.relationship("User", foreign_keys=[addressee_id])


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(2000), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sender = db.relationship("User", foreign_keys=[sender_id])
    receiver = db.relationship("User", foreign_keys=[receiver_id])


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def invitation_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if request.method == "POST" and request.form.get("invitation", "") != os.environ.get("INVITATION_CODE", "Ylianna"):
            flash("Le code d’invitation est incorrect.", "error")
            return redirect(url_for("register"))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_notifications():
    unread = Notification.query.filter_by(user_id=current_user.id, read=False).count() if current_user.is_authenticated else 0
    return {"unread_notifications": unread}


@app.route("/")
def index():
    return redirect(url_for("feed" if current_user.is_authenticated else "login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip().lower()
        user = User.query.filter(or_(db.func.lower(User.email) == identifier, db.func.lower(User.username) == identifier, User.phone == request.form.get("identifier", "").strip())).first()
        if user and user.check_password(request.form.get("password", "")):
            login_user(user, remember=bool(request.form.get("remember")))
            return redirect(url_for("feed"))
        flash("Identifiants invalides.", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
@invitation_required
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip() or None
        password = request.form.get("password", "")
        if len(username) < 3 or len(password) < 8 or "@" not in email:
            flash("Nom, email ou mot de passe invalide (8 caractères minimum).", "error")
        elif User.query.filter(or_(User.username == username, User.email == email, User.phone == phone) if phone else or_(User.username == username, User.email == email)).first():
            flash("Ce nom ou cet email est déjà utilisé.", "error")
        else:
            user = User(username=username, email=email, phone=phone)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("feed"))
    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/feed", methods=["GET", "POST"])
@login_required
def feed():
    if request.method == "POST":
        body = request.form.get("body", "").strip()
        if body and len(body) <= 2000:
            db.session.add(Post(body=body, user_id=current_user.id))
            db.session.commit()
        return redirect(url_for("feed"))
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template("feed.html", posts=posts)


@app.post("/post/<int:post_id>/like")
@login_required
def like(post_id):
    like = Like.query.filter_by(post_id=post_id, user_id=current_user.id).first()
    if like:
        db.session.delete(like)
    else:
        db.session.add(Like(post_id=post_id, user_id=current_user.id))
    db.session.commit()
    return redirect(request.referrer or url_for("feed"))


@app.post("/post/<int:post_id>/comment")
@login_required
def comment(post_id):
    body = request.form.get("body", "").strip()
    if body:
        db.session.add(Comment(body=body[:500], post_id=post_id, user_id=current_user.id))
        db.session.commit()
    return redirect(request.referrer or url_for("feed"))


@app.route("/profile/<username>")
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template("profile.html", profile=user, posts=Post.query.filter_by(user_id=user.id).order_by(Post.created_at.desc()).all())


@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        bio = request.form.get("bio", "").strip()[:180]
        avatar = request.form.get("avatar", "").strip()[:255]
        duplicate = User.query.filter(User.username == username, User.id != current_user.id).first()
        if len(username) < 3 or len(username) > 30:
            flash("Le nom d’utilisateur doit contenir entre 3 et 30 caractères.", "error")
        elif duplicate:
            flash("Ce nom d’utilisateur est déjà pris.", "error")
        else:
            current_user.username = username
            current_user.bio = bio or "Bienvenue sur Ylohann !"
            current_user.avatar = avatar or current_user.avatar
            db.session.commit()
            flash("Profil mis à jour.", "success")
            return redirect(url_for("profile", username=current_user.username))
    return render_template("edit_profile.html")


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        section = request.form.get("section")
        if section == "profile":
            username = request.form.get("username", "").strip()
            duplicate = User.query.filter(User.username == username, User.id != current_user.id).first()
            if len(username) < 3 or len(username) > 30:
                flash("Le nom d’utilisateur doit contenir entre 3 et 30 caractères.", "error")
            elif duplicate:
                flash("Ce nom d’utilisateur est déjà pris.", "error")
            else:
                current_user.username = username
                current_user.bio = request.form.get("bio", "").strip()[:180] or "Bienvenue sur Ylohann !"
                current_user.avatar = request.form.get("avatar", "").strip()[:255] or current_user.avatar
                db.session.commit()
                flash("Profil mis à jour.", "success")
        elif section == "password":
            new_password = request.form.get("new_password", "")
            if not current_user.check_password(request.form.get("current_password", "")):
                flash("L’ancien mot de passe est incorrect.", "error")
            elif len(new_password) < 8 or new_password != request.form.get("confirm_password", ""):
                flash("Le nouveau mot de passe doit contenir 8 caractères et être confirmé.", "error")
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash("Mot de passe modifié.", "success")
        elif section == "contact":
            email = request.form.get("email", "").strip().lower()
            phone = request.form.get("phone", "").strip() or None
            email_taken = User.query.filter(User.email == email, User.id != current_user.id).first()
            phone_taken = phone and User.query.filter(User.phone == phone, User.id != current_user.id).first()
            if "@" not in email or email_taken or phone_taken:
                flash("Cet email ou ce numéro est invalide ou déjà utilisé.", "error")
            else:
                current_user.email = email
                current_user.phone = phone
                db.session.commit()
                flash("Coordonnées mises à jour.", "success")
        return redirect(url_for("settings"))
    return render_template("settings.html")


@app.route("/friends", methods=["GET", "POST"])
@login_required
def friends():
    if request.method == "POST":
        target = User.query.filter_by(username=request.form.get("username", "").strip()).first()
        if target and target.id != current_user.id:
            exists = Friendship.query.filter(or_(db.and_(Friendship.requester_id == current_user.id, Friendship.addressee_id == target.id), db.and_(Friendship.requester_id == target.id, Friendship.addressee_id == current_user.id))).first()
            if not exists:
                db.session.add(Friendship(requester_id=current_user.id, addressee_id=target.id))
                db.session.add(Notification(text=f"{current_user.username} vous a envoyé une demande.", user_id=target.id))
                db.session.commit()
        return redirect(url_for("friends"))
    received = Friendship.query.filter_by(addressee_id=current_user.id, status="pending").all()
    accepted = Friendship.query.filter(or_(db.and_(Friendship.requester_id == current_user.id, Friendship.status == "accepted"), db.and_(Friendship.addressee_id == current_user.id, Friendship.status == "accepted"))).all()
    return render_template("friends.html", received=received, accepted=accepted)


@app.post("/friends/<int:friendship_id>/accept")
@login_required
def accept_friend(friendship_id):
    friendship = db.session.get(Friendship, friendship_id)
    if friendship and friendship.addressee_id == current_user.id:
        friendship.status = "accepted"
        db.session.commit()
    return redirect(url_for("friends"))


@app.route("/messages")
@login_required
def inbox():
    friendships = Friendship.query.filter(or_(db.and_(Friendship.requester_id == current_user.id, Friendship.status == "accepted"), db.and_(Friendship.addressee_id == current_user.id, Friendship.status == "accepted"))).all()
    friends_list = [item.addressee if item.requester_id == current_user.id else item.requester for item in friendships]
    return render_template("messages_inbox.html", friends_list=friends_list)


@app.route("/messages/<username>", methods=["GET", "POST"])
@login_required
def messages(username):
    other = User.query.filter_by(username=username).first_or_404()
    if request.method == "POST":
        body = request.form.get("body", "").strip()
        if body:
            db.session.add(Message(body=body[:2000], sender_id=current_user.id, receiver_id=other.id))
            db.session.commit()
        return redirect(url_for("messages", username=username))
    conversation = Message.query.filter(or_(db.and_(Message.sender_id == current_user.id, Message.receiver_id == other.id), db.and_(Message.sender_id == other.id, Message.receiver_id == current_user.id))).order_by(Message.created_at.asc()).all()
    return render_template("messages.html", other=other, conversation=conversation)


@app.route("/notifications")
@login_required
def notifications():
    items = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    for item in items:
        item.read = True
    db.session.commit()
    return render_template("notifications.html", items=items)


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
