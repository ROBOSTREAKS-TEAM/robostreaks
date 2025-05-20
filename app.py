from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from pymongo import MongoClient
from bson.objectid import ObjectId
from wtforms import StringField, PasswordField, SubmitField, FileField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, Email
from flask_wtf.file import FileAllowed, FileRequired
from flask_wtf import FlaskForm
from werkzeug.utils import secure_filename
from functools import wraps 
from collections import defaultdict
import os
import dotenv
from math import ceil
import requests
from io import BytesIO
from PIL import Image

# Load environment variables
dotenv.load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback_secret_key")

# MongoDB Setup
client = MongoClient(os.getenv("MONGO_URI"))
db = client.robostreaks

# Collections
content_collection = db.content
team_collection = db.team
testimonial_collection = db.testimonials
users_collection = db.users  # For admin login
alumni_collection = db.alumni

# Set default rating of 5 for testimonials without it
db.testimonials.update_many(
    {"rating": {"$exists": False}},
    {"$set": {"rating": 5}}
)

# Admin Login Form
class LoginForm(FlaskForm):
    username = StringField('Username')
    password = PasswordField('Password')
    submit = SubmitField('Login')

class AlumniForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired()])
    role = StringField('Role', validators=[DataRequired()])
    workplace = StringField('Workplace', validators=[DataRequired()])
    linkedin = StringField('LinkedIn URL')
    github = StringField('GitHub URL')
    email = StringField('Email', validators=[Email()])
    instagram = StringField('Instagram URL')
    grad_year = IntegerField('Graduation Year')
    bio = TextAreaField('Short Bio')
    photo = FileField('Upload Photo', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    submit = SubmitField('Register')

# Set upload folder
UPLOAD_FOLDER = 'static/uploads/team'
ALUMNI_UPLOAD_FOLDER = 'static/uploads/alumni'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ALUMNI_UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALUMNI_UPLOAD_FOLDER'] = ALUMNI_UPLOAD_FOLDER

# Admin Login Check
def is_admin_logged_in():
    return 'admin' in session

# Helper function to download and save remote image
def download_and_save_image(url, save_path):
    try:
        response = requests.get(url, stream=True, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            img.save(save_path)
            return True
        return False
    except Exception as e:
        print("Error downloading image:", str(e))
        return False

# Flag to ensure sample data is inserted only once
sample_data_inserted = False

@app.before_request
def insert_sample_data_once():
    global sample_data_inserted
    if not sample_data_inserted:
        # Check if collection is empty
        if team_collection.count_documents({}) == 0:
            sample_team = [
                {
                    "name": "Dr. Chitta Ranjan Mohanty",
                    "role": "Principal",
                    "image": "prof.-cr-mohanty.jpg"
                },
                {
                    "name": "Mr. Aditya Patra",
                    "role": "Professor In Charge(PIC)",
                    "image": "aditya_patra.jpg"
                },
                {
                    "name": "Dr. Niranjan Panigrahi",
                    "role": "Faculty Adviser",
                    "image": "niranjan_panigrahi.jpg"
                }
            ]
            team_collection.insert_many(sample_team)
        sample_data_inserted = True

# Routes
@app.route('/')
def home():
    about = content_collection.find_one({"section": "about"})
    wings_left = list(db.wings.find({"position": "left"}))
    wings_right = list(db.wings.find({"position": "right"}))
    team = list(team_collection.find({}).sort("order", 1).limit(6))  # 👈 LIMIT TO 6
    testimonials = list(testimonial_collection.find({}))
    return render_template('landing.html',
                           about=about,
                           team=team,
                           testimonials=testimonials,
                           wings_left=wings_left,
                           wings_right=wings_right)

@app.route('/team')
def team():
    members = list(team_collection.find())
    grouped = defaultdict(list)
    wings_grouped = defaultdict(list)
    for m in members:
        cat = m.get('category', 'Others')
        if cat == 'Wings Coordinators':
            sub_cat = m.get('sub_category', 'Others')
            wings_grouped[sub_cat].append(m)
        else:
            grouped[cat].append(m)
    return render_template('team.html', grouped_team=grouped, wings_team=wings_grouped)

@app.route('/admin/team', methods=['GET', 'POST'])
def admin_team():
    edit_id = request.args.get('edit_id')
    member_to_edit = None
    if edit_id:
        member_to_edit = db.team.find_one({'_id': ObjectId(edit_id)})
    # ✅ Fetch about content
    about = db.about.find_one()
    team = list(db.team.find().sort("order", 1))
    testimonials = list(db.testimonials.find())
    return render_template('admin_dashboard.html',
                           team=team,
                           about=about,
                           testimonials=testimonials,
                           edit_member=member_to_edit)

# Admin Login Route
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        # Check against .env values
        correct_username = os.getenv("ADMIN_USERNAME")
        correct_password = os.getenv("ADMIN_PASSWORD")
        if username == correct_username and password == correct_password:
            session['admin'] = username
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid admin credentials")
    return render_template('admin_login.html', form=form)

# Admin Required Decorator
def admin_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'admin' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return wrap

# Admin Dashboard Route (Protected)
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    about = content_collection.find_one({"section": "about"}) or {"content": "", "section": "about"}
    wings_left = list(db.wings.find({"position": "left"}))
    wings_right = list(db.wings.find({"position": "right"}))
    team = list(team_collection.find({}))
    testimonials = list(testimonial_collection.find({}))
    return render_template('admin_dashboard.html',
                           about=about,
                           wings_left=wings_left,
                           wings_right=wings_right,
                           team=team,
                           testimonials=testimonials)

@app.route('/admin/update/about', methods=['POST'])
def update_about():
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    content = request.form.get('content')
    db.content.update_one(
        {"section": "about"},
        {"$set": {"content": content}},
        upsert=True
    )
    flash("About section updated.")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update/wing/<wing_id>', methods=['POST'])
def update_wing(wing_id):
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    title = request.form.get('title')
    description = request.form.get('description')
    icon = request.form.get('icon')
    db.wings.update_one(
        {"_id": ObjectId(wing_id)},
        {"$set": {"title": title, "description": description, "icon": icon}}
    )
    flash("Wing updated.")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add/wing', methods=['POST'])
def add_wing():
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    title = request.form.get('title')
    description = request.form.get('description')
    icon = request.form.get('icon')
    position = request.form.get('position')  # left or right
    db.wings.insert_one({
        "title": title,
        "description": description,
        "icon": icon,
        "position": position
    })
    flash("New wing added.")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/upload/image', methods=['POST'])
def upload_image():
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    if 'photo' not in request.files:
        flash("No file part")
        return redirect(url_for('admin_dashboard'))
    photo = request.files['photo']
    if photo.filename == '':
        flash("No selected file")
        return redirect(url_for('admin_dashboard'))
    try:
        filename = secure_filename(photo.filename)
        upload_path = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], filename)
        photo.save(upload_path)
        flash(f"✅ Image uploaded: /{app.config['UPLOAD_FOLDER']}/{filename}")
    except Exception as e:
        flash(f"❌ Error uploading file: {str(e)}")
    return redirect(url_for('admin_dashboard'))

@app.route("/add_team_member", methods=["POST"])
def add_team_member():
    name = request.form["name"]
    role = request.form["role"]
    order = int(request.form["order"])

    # Handle image upload
    photo = request.files.get("photo")
    if photo and photo.filename != '':
        filename = secure_filename(photo.filename)
        photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        image = filename
    else:
        image = "default.jpg"  # Fallback image

    new_member = {
        "name": name,
        "role": role,
        "image": image,
        "order": order,
        "category": request.form.get("category"),
        "sub_category": request.form.get("sub_category") if request.form.get("category") == "Wings Coordinators" else None,
        "facebook": request.form.get("facebook", ""),
        "instagram": request.form.get("instagram", ""),
        "twitter": request.form.get("twitter", ""),
        "linkedin": request.form.get("linkedin", "")
    }

    db.team.insert_one(new_member)
    return redirect(url_for("admin_team"))

# Edit Member Form
from flask import request, redirect, url_for, render_template

@app.route('/edit_team_member/<id>', methods=['GET', 'POST'])
def edit_team_member(id):
    member = db.team.find_one({"_id": ObjectId(id)})
    categories = ['Leadership', 'Faculty', 'Wings Coordinators', 'Core Team', 'Others']
    subcategories = {
        'Wings Coordinators': ['Robotics Wing', 'Programming Wing', 'Management Wing']
    }
    if request.method == "POST":
        update_data = {
            "name": request.form["name"],
            "role": request.form["role"],
            "image": request.form["image"],
            "order": int(request.form.get("order", 0)),
            "category": request.form.get("category", ""),
            "subcategory": request.form.get("subcategory", ""),
            "facebook": request.form.get("facebook", ""),
            "instagram": request.form.get("instagram", ""),
            "twitter": request.form.get("twitter", ""),
            "linkedin": request.form.get("linkedin", "")
        }
        db.team.update_one({"_id": ObjectId(id)}, {"$set": update_data})
        return redirect(url_for('admin_team'))
    return render_template(
        'edit_team_member.html',
        member=member,
        categories=categories,
        subcategories=subcategories
    )

# Update Member
@app.route('/update_team_member/<id>', methods=['POST'])
def update_team_member(id):
    updated_data = {
        "name": request.form["name"],
        "role": request.form["role"],
        "order": int(request.form["order"]),
        "category": request.form.get("category"),
        "sub_category": request.form.get("sub_category") if request.form.get("category") == "Wings Coordinators" else None,
        "facebook": request.form.get("facebook"),
        "instagram": request.form.get("instagram"),
        "twitter": request.form.get("twitter"),
        "linkedin": request.form.get("linkedin"),
    }

    # Handle image upload
    photo = request.files.get("photo")
    if photo and photo.filename != '':
        filename = secure_filename(photo.filename)
        photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        updated_data["image"] = filename

    db.team.update_one({"_id": ObjectId(id)}, {"$set": updated_data})
    return redirect(url_for("admin_team"))

@app.route('/admin/add_testimonial', methods=['POST'])
def add_testimonial():
    quote = request.form['quote']
    author = request.form['author']
    rating = int(request.form.get('rating', 5))
    image = request.form['image']
    testimonial_collection.insert_one({
        'quote': quote,
        'author': author,
        'rating': rating,
        'image': image
    })
    return redirect(url_for('admin_dashboard'))  

@app.route('/admin/team/delete/<id>')
def delete_team_member(id):
    if not is_admin_logged_in():
        return redirect(url_for('admin_login'))
    team_collection.delete_one({"_id": ObjectId(id)})
    flash("🗑️ Team member deleted.")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/update_testimonial/<id>', methods=['POST'])
def update_testimonial(id):
    quote = request.form['quote']
    author = request.form['author']
    rating = int(request.form.get(f'rating_{id}', 5))
    image = request.form['image']
    testimonial_collection.update_one(
        {'_id': ObjectId(id)},
        {'$set': {
            'quote': quote,
            'author': author,
            'rating': rating,
            'image': image
        }}
    )
    return redirect(url_for('admin_dashboard'))

# Alumni Registration Route (Updated)
@app.route('/alumni/register', methods=['GET', 'POST'])
def alumni_register():
    form = AlumniForm()
    if form.validate_on_submit():
        file = form.photo.data
        filename = secure_filename(file.filename)
        photo_path = os.path.join(app.config['ALUMNI_UPLOAD_FOLDER'], filename)
        file.save(photo_path)

        alumni_data = {
            "name": form.name.data,
            "role": form.role.data,
            "workplace": form.workplace.data,
            "linkedin": form.linkedin.data,
            "github": form.github.data,
            "email": form.email.data,
            "instagram": form.instagram.data,
            "grad_year": form.grad_year.data,
            "bio": form.bio.data,
            "photo": f"alumni/{filename}"
        }

        db.alumni.insert_one(alumni_data)
        flash("✅ Alumni registered successfully!")
        return redirect(url_for('alumni'))

    return render_template('alumni_register.html', form=form)


# Serve Alumni Images
@app.route('/static/uploads/alumni/<filename>')
def uploaded_alumni_file(filename):
    return send_from_directory(app.config['ALUMNI_UPLOAD_FOLDER'], filename)


# Alumni Listing Page
@app.route('/alumni')
def alumni():
    search_query = request.args.get('search', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 6

    query = {}
    if search_query:
        query['$or'] = [
            {"name": {"$regex": search_query, "$options": "i"}},
            {"role": {"$regex": search_query, "$options": "i"}},
            {"workplace": {"$regex": search_query, "$options": "i"}},
            {"grad_year": {"$regex": search_query, "$options": "i"}}
        ]

    total = db.alumni.count_documents(query)
    alumni_cursor = db.alumni.find(query).skip((page - 1) * per_page).limit(per_page)
    alumni = list(alumni_cursor)

    pagination = {
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': ceil(total / per_page),
        'has_prev': page > 1,
        'has_next': page * per_page < total,
        'prev_num': page - 1,
        'next_num': page + 1,
    }

    return render_template('alumni.html', alumni=alumni, pagination=pagination)



# Multi-step Alumni Registration (Optional - If You Want to Use It Later)
@app.route('/alumni/register/step1', methods=['GET', 'POST'])
def alumni_register_step1():
    if request.method == 'POST':
        session['alumni_step1'] = {
            'name': request.form.get('name', ''),
            'role': request.form.get('role', ''),
            'workplace': request.form.get('workplace', '')
        }

        if not session['alumni_step1']['name']:
            flash("Name is required.")
            return redirect(url_for('alumni_register_step1'))

        return redirect(url_for('alumni_register_step2'))

    data = session.get('alumni_step1', {})
    return render_template('alumni_register_step1.html', data=data)


@app.route('/alumni/register/step2', methods=['GET', 'POST'])
def alumni_register_step2():
    if 'alumni_step1' not in session:
        return redirect(url_for('alumni_register_step1'))

    if request.method == 'POST':
        session['alumni_step2'] = {
            'linkedin': request.form.get('linkedin', ''),
            'github': request.form.get('github', ''),
            'email': request.form.get('email', ''),
            'instagram': request.form.get('instagram', ''),
            'grad_year': request.form.get('grad_year', ''),
            'bio': request.form.get('bio', ''),
            'photo': ''
        }

        photo = request.files.get('photo')
        if photo and photo.filename != '':
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['ALUMNI_UPLOAD_FOLDER'], filename))
            session['alumni_step2']['photo'] = filename

        alumni_data = {
            **session['alumni_step1'],
            **session['alumni_step2'],
            "photo": session['alumni_step2']['photo']
        }

        db.alumni.insert_one(alumni_data)
        session.pop('alumni_step1', None)
        session.pop('alumni_step2', None)
        flash("✅ Registration complete!")
        return redirect(url_for('alumni'))

    data = session.get('alumni_step2', {})
    return render_template('alumni_register_step2.html', data=data)


# Optional: Delete this if you're using single-step form
@app.route('/alumni/submit', methods=['GET', 'POST'])
def alumni_submit():
    if request.method == 'POST':
        name = request.form.get('name')
        role = request.form.get('role')
        workplace = request.form.get('workplace')
        photo = request.files.get('photo')
        if photo:
            filename = secure_filename(photo.filename)
            photo.save(os.path.join('static/uploads/alumni', filename))
        else:
            filename = ""
        db.alumni.insert_one({
            "name": name,
            "role": role,
            "workplace": workplace,
            "photo": f"/static/uploads/alumni/{filename}" if filename else ""
        })
        flash("✅ Submitted successfully!")
        return redirect(url_for('home'))
    return render_template('alumni_submit.html')


# Logout
@app.route('/admin/logout')
def logout():
    session.pop('admin', None)
    flash("✅ Logged out successfully.")
    return redirect(url_for('home'))


# Serve uploaded files
@app.route('/static/uploads/team/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)




if __name__ == '__main__':
    app.run(debug=True)
