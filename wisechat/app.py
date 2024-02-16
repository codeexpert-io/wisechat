from time import localtime, strftime
from flask import Flask, render_template, redirect, url_for, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, EqualTo, ValidationError
from flask_sqlalchemy import SQLAlchemy
from passlib.hash import pbkdf2_sha256
from flask_login import LoginManager, UserMixin, login_user, current_user, login_required, logout_user
from flask_socketio import SocketIO, send, emit, join_room, leave_room

# configure app
app = Flask(__name__)
app.secret_key = 'replace later'

#configure database
app.config['SQLALCHEMY_DATABASE_URI']='postgresql://postgres.zqmibadinmfjdpvrbvpm:Nengimote123!@aws-0-us-west-1.pooler.supabase.com:5432/postgres'
db = SQLAlchemy(app)

#Initialize Flask-SocketIO
socketio = SocketIO(app)
ROOMS = ['lounge', 'news', 'games', 'coding']


#Congfigure flask login
login = LoginManager(app)
login.init_app(app)

#models
class User(UserMixin, db.Model):
    '''User model'''

    __tablename__='users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), unique=True, nullable=False)
    password = db.Column(db.String(), nullable=False)



#wtform_fields
def invalid_credentials(form, field):
    '''Username and password checker'''
    username_entered = form.username.data
    password_entered = field.data

    #check credentials is valid
    user_object = User.query.filter_by(username=username_entered).first()
    if user_object is None:
        raise ValidationError("Username or password is incorrect")
    elif not pbkdf2_sha256.verify(password_entered,user_object.password):
        raise ValidationError("Username or password is incorrect")


class RegistrationForm(FlaskForm):
    '''Registration Form'''

    username = StringField('username_label', validators=[InputRequired(message="Username required"),
                                                         Length(min=4, max=25,
                                                                message="Username must be between 4 and 25 characters")])
    password = PasswordField('password_label', validators=[InputRequired(message="Password required"),
                                                         Length(min=4, max=25,
                                                                message="Username must be between 4 and 25 characters")])
    confirm_pswd = PasswordField('confirm_pswd_label', validators=[InputRequired(message="Username required"),
                                                         EqualTo('password', message="Passwords must match")])
    submit_button = SubmitField('Create')

    def validate_username(self, username):
        user_object = User.query.filter_by(username=username.data).first()
        if user_object:
            raise ValidationError("Username already exists. Select a different username.")

class LoginForm(FlaskForm):
    '''Login form'''

    username = StringField('username_label',
                           validators=[InputRequired(message="Username required")])
    password = PasswordField('password_label',
                           validators=[InputRequired(message="Password required"),
                                       invalid_credentials])
    submit_button = SubmitField('Login')



#app


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


@app.route('/', methods = ['GET', 'POST'])
def index():

    reg_form = RegistrationForm()

    #Updated database if validation success
    if reg_form.validate_on_submit():
        username = reg_form.username.data
        password = reg_form.password.data

        hashed_pswd=pbkdf2_sha256.hash(password)

        #Add user to DB
        user = User(username=username, password=hashed_pswd)
        db.session.add(user)
        db.session.commit()

        flash('Registered successfully. Please login.','success')

        return redirect(url_for('login'))

    return render_template("index.html", form=reg_form)


@app.route("/login", methods=['GET','POST'])
def login():

    login_form = LoginForm()

    #Allows login if validation success
    if login_form.validate_on_submit():
        user_object=User.query.filter_by(username=login_form.username.data).first()
        login_user(user_object)
        return redirect(url_for('chat'))

    return render_template('login.html', form=login_form)


@app.route("/chat", methods=['GET','POST'])
def chat():

    if not current_user.is_authenticated:
         flash('Please login.','danger')
         return redirect(url_for('login'))

    return render_template('chat.html',username=current_user.username, rooms=ROOMS)


@app.route("/logout", methods=['GET'])
def logout():

    logout_user()
    flash('You have logged out successfully', 'success')
    return redirect(url_for('login'))


@socketio.on('message')
def message(data):

    print(f"\n\n{data}\n\n")
    send({'msg':data['msg'], 'username': data['username'], 'time_stamp': strftime('%b-%d %I:%M%p', localtime())}, room=data['room'])

@socketio.on('join')
def join(data):
    join_room(data['room'])
    send({'msg': data['username'] + " has joined the " + data['room'] + " room."},
         room=data["room"])

@socketio.on('leave')
def leave(data):

    leave_room(data['room'])
    send({'msg': data['username'] + " has left the " + data['room'] + " room."},
         room=data["room"])




if __name__=='__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)