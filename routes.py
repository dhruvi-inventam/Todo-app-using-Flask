from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from sqlalchemy import func
from datetime import datetime, date, timedelta
from flask import request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import case


from app import app, db, login_manager
from models import User, Todo

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

from sqlalchemy import case

@app.route('/')
@login_required
def index():
    today = date.today()
    now = datetime.now()
    sort = request.args.get('sort')

    query = Todo.query.filter(
        Todo.user_id == current_user.id,
        Todo.due_date != None,
        db.func.date(Todo.due_date) == today
    )

    # Apply sorting
    if sort == 'due_date_asc':
        query = query.order_by(Todo.due_date.asc())
    elif sort == 'due_date_desc':
        query = query.order_by(Todo.due_date.desc())
    elif sort == 'priority':
        # Custom sort: High > Medium > Low
        priority_order = case(
            (Todo.priority == 'High', 1),
            (Todo.priority == 'Medium', 2),
            (Todo.priority == 'Low', 3),
            else_=4
        )
        query = query.order_by(priority_order)

    tasks = query.all()

    return render_template('index.html', tasks=tasks, selected_date=today, now=now, active_tab='today')

@app.route('/add', methods=['POST'])
@login_required
def add():
    title = request.form['title']
    description = request.form['description']
    priority = request.form['priority']
    category = request.form['category']

    # Handle due date and reminder
    due_input = request.form['due_date']
    reminder_input = request.form['reminder_time']

    due_date = datetime.strptime(due_input, '%Y-%m-%dT%H:%M') if due_input else None
    reminder_time = datetime.strptime(reminder_input, '%Y-%m-%dT%H:%M') if reminder_input else None

    # Create the new task
    new_task = Todo(
        title=title,
        description=description,
        priority=priority,
        category=category,
        due_date=due_date,
        reminder_time=reminder_time,
        completed=False,
        owner=current_user
    )

    db.session.add(new_task)
    db.session.commit()

    flash("Task added successfully!", "success")
    return redirect(url_for('index'))


@app.route('/delete/<int:id>')
@login_required
def delete(id):
    task = Todo.query.get_or_404(id)
    if task.owner != current_user:
        return "Unauthorized", 403
    db.session.delete(task)
    db.session.commit()
    return redirect('/')

@app.route('/update/<int:id>', methods=['GET', 'POST'])
@login_required
def update(id):
    task = Todo.query.get_or_404(id)
    if task.owner != current_user:
        return "Unauthorized", 403
    if request.method == 'POST':
        task.title = request.form['title']
        task.description = request.form['description']
        task.priority = request.form['priority']
        task.category = request.form['category']
        due_input = request.form['due_date']
        task.due_date = datetime.strptime(due_input, '%Y-%m-%dT%H:%M') if due_input else None
        db.session.commit()
        return redirect('/')
    return render_template('update.html', task=task)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        if User.query.filter_by(username=username).first():
            return "User already exists"
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            now = datetime.now()
            reminders = Todo.query.filter(
                Todo.user_id == user.id,
                Todo.completed == False,
                Todo.reminder_time != None,
                Todo.reminder_time <= now
            ).all()

            if reminders:
                flash(f"You have {len(reminders)} reminder(s) due!", "warning")
            return redirect('/')
        return "Invalid credentials"
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

@app.route('/category/<string:name>')
@login_required
def category(name):
    allowed_categories = ['Work', 'Personal', 'Other']
    if name.capitalize() not in allowed_categories:
        return "Category not found", 404

    tasks = Todo.query.filter_by(user_id=current_user.id, category=name.capitalize()).order_by(Todo.created_at.desc()).all()
    return render_template('category.html', tasks=tasks, category=name.capitalize())

@app.route('/date/<date_str>')
@login_required
def todos_by_date(date_str):
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return "Invalid date format", 400

    tasks = Todo.query.filter(
        Todo.user_id == current_user.id,
        Todo.due_date != None,
        func.date(Todo.due_date) == selected_date
    ).all()
    now = datetime.now()
    return render_template('index.html', tasks=tasks, selected_date=selected_date, now=now)

@app.route('/complete/<int:id>', methods=['POST'])
@login_required
def mark_complete(id):
    task = Todo.query.get_or_404(id)
    if task.owner != current_user:
        return "Unauthorized", 403
    task.completed = True
    db.session.commit()
    flash("Task marked as completed!", "success")
    return redirect(request.referrer or '/')

@app.route('/tasks/all')
@login_required
def all_tasks():
    now = datetime.now()
    tasks = Todo.query.filter_by(user_id=current_user.id).all()
    return render_template('index.html', tasks=tasks, selected_date=date.today(), now=now, active_tab='all')


@app.route('/tasks/upcoming')
@login_required
def upcoming_tasks():
    now = datetime.now()

    tasks = Todo.query.filter(
        Todo.user_id == current_user.id,
        Todo.completed == False,
        Todo.due_date != None,
        Todo.due_date > now  # this filters only future tasks
    ).order_by(Todo.due_date.asc()).all()

    return render_template(
        'index.html',
        tasks=tasks,
        selected_date=now.date(),
        now=now,
        active_tab='upcoming'
    )
@app.route('/tasks/completed')
@login_required
def completed_tasks():
    now = datetime.now()
    tasks = Todo.query.filter_by(user_id=current_user.id, completed=True).all()
    return render_template('index.html', tasks=tasks, selected_date=date.today(), now=now, active_tab='completed')

@app.route('/tasks/overdue')
@login_required
def overdue_tasks():
    now = datetime.now()
    tasks = Todo.query.filter(
        Todo.user_id == current_user.id,
        Todo.completed == False,
        Todo.due_date != None,
        Todo.due_date < now
    ).all()
    return render_template('index.html', tasks=tasks, selected_date=date.today(), now=now, active_tab='overdue')
