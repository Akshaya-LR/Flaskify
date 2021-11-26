from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
from data import articles
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)

# Configure MySql Database

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'myflask'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

# Article = articles()


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/articles')
def articles():
    my_cursor = mysql.connection.cursor()
    # user = session['username']
    articles_data = my_cursor.execute('SELECT * FROM article_table')

    result = my_cursor.fetchall()

    return render_template('article.html', articles=result)
    my_cursor.close()


@app.route('/articles/<string:id>/')
def article_id(id):
    my_cursor = mysql.connection.cursor()
    # user = session['username']
    articles_data = my_cursor.execute('SELECT * FROM article_table WHERE id=%s', [id])

    result = my_cursor.fetchone()

    if articles_data > 0:
        return render_template('sep_article.html', article=result)
        print(result)
    else:
        return render_template('dashboard.html', message='No articles found')
    my_cursor.close()


# Create Registration Form using WTForms

class RegistrationForm(Form):
    name = StringField('Name', [validators.Length(min=3, max=30)])
    username = StringField('Username', [validators.Length(min=4, max=20)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        # Create a Cursor
        my_cursor = mysql.connection.cursor()

        my_cursor.execute('INSERT INTO users(name, email, username, password) VALUES (%s, %s, %s, %s)', (name, email,
                                                                                                         username,
                                                                                                         password))

        # Commit the changes to DB
        mysql.connection.commit()

        # Close the connection
        my_cursor.close()

        # Use flash messages to inform users that they have registered
        flash("Registration success", 'success')

        return redirect(url_for('home'))

    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get the info - username and password from the form
        username = request.form['username']
        passwd = request.form['password']

        # Create a cursor to check with the DB
        my_cursor = mysql.connection.cursor()
        result = my_cursor.execute('SELECT * FROM users WHERE username = %s', [username])

        if result > 0:
            user_data = my_cursor.fetchone()
            user_password = user_data['password']

            if sha256_crypt.verify(passwd, user_password):
                session['logged_in'] = True
                session['username'] = username
                flash('Login success', 'success')
                return redirect(url_for('dashboard'))
            else:
                return render_template('login.html', error='Invalid Login')
            my_cursor.close()
        else:
            return render_template('login.html', error='User does not exist. Please register.')
    return render_template('login.html')


def is_logged_in(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'logged_in' in session:
            return func(*args, **kwargs)
        else:
            flash('Unauthorized. Please login', 'danger')
            return redirect(url_for('login'))
    return wrapper


@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('Logout success', 'success')
    return redirect(url_for('login'))


@app.route('/dashboard')
@is_logged_in
def dashboard():
    my_cursor = mysql.connection.cursor()
    user = session['username']
    articles_data = my_cursor.execute('SELECT * FROM article_table WHERE author=%s', [user])

    result = my_cursor.fetchall()

    if articles_data > 0:
        return render_template('dashboard.html', articles=result)
    else:
        return render_template('dashboard.html', message='No articles found')
    my_cursor.close()


# Get article form from the user
class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=300)])
    content = TextAreaField('content', [validators.Length(min=25)])


# Add articles
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.content.data

        my_cursor = mysql.connection.cursor()

        my_cursor.execute('INSERT INTO article_table(title, body, author) VALUES(%s, %s, %s)', (title, body,
                                                                                                session['username']))

        mysql.connection.commit()

        my_cursor.close()

        flash('Article created', 'success')

        return redirect(url_for('dashboard'))
    return render_template('add_article.html', form=form)


# Edit articles
@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
    my_cursor = mysql.connection.cursor()

    result = my_cursor.execute('SELECT * FROM article_table WHERE id=%s', [id])

    article = my_cursor.fetchone()

    form = ArticleForm(request.form)

    # Pre-populate the fields
    form.title.data = article['title']
    form.content.data = article['body']

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['content']

        my_cursor = mysql.connection.cursor()

        my_cursor.execute('UPDATE article_table SET title=%s, body=%s WHERE id=%s', (title, body, id))

        mysql.connection.commit()

        my_cursor.close()

        flash('Article Updated', 'success')

        return redirect(url_for('dashboard'))
    return render_template('edit_article.html', form=form)


@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    my_cursor = mysql.connection.cursor()

    my_cursor.execute('DELETE FROM article_table WHERE id=%s', [id])

    mysql.connection.commit()

    my_cursor.close()
    flash('Article Deleted', 'success')

    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.secret_key = 'secret12'
    app.run(debug=True)
