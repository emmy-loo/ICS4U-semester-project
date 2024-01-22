from flask import Blueprint, render_template, request, flash, jsonify, Response
from flask_login import login_required, current_user
from .models import Expense, Note
from . import db
import json
from datetime import datetime, timedelta
from .models import Budget
import pandas as pd

views = Blueprint('views', __name__)


@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == 'POST': 
        note = request.form.get('note')#Gets the note from the HTML 

        if len(note) < 1:
            flash('Note is too short!', category='error') 
        else:
            new_note = Note(data=note, user_id=current_user.id)  #providing the schema for the note 
            db.session.add(new_note) #adding the note to the database 
            db.session.commit()
            flash('Note added!', category='success')

    return render_template("home.html", user=current_user)

@views.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    all_expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()
    # Retrieve the last five expenses and calculate the total amount
    last_five_expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).limit(5).all()
    total_expenses = db.session.query(db.func.sum(Expense.amount)).filter_by(user_id=current_user.id).scalar() or 0
    expense_distribution = {}
    all_expenses = Expense.query.filter_by(user_id=current_user.id).all()
    for expense in all_expenses:
        if total_expenses > 0:
            percentage = (expense.amount / total_expenses) * 100
        else:
            percentage = 0
        expense_distribution[expense.category] = round(percentage, 2)
     # Create a Pandas DataFrame for export
    data = {
        'Description': [expense.description for expense in all_expenses],
        'Category': [expense.category for expense in all_expenses],
        'Date': [expense.date.strftime('%Y-%m-%d') for expense in all_expenses],
        'Amount': [f'${expense.amount:.2f}' for expense in all_expenses],
        'Percentage': [f'{expense_distribution[expense.category]:.2f}%' for expense in all_expenses],
    }
    df = pd.DataFrame(data)

    # Export to Excel
    excel_filename = 'dashboard_data.xlsx'
    df.to_excel(excel_filename, index=False)
    return render_template("dashboard.html", user=current_user, last_five_expenses=last_five_expenses, total_expenses=total_expenses, expense_distribution=expense_distribution, excel_filename=excel_filename)
    
@views.route('/download-excel/<filename>')
def download_excel(filename):
    return Response(
        open(filename, 'rb').read(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment;filename={filename}"},
    )

@views.route('/delete-note', methods=['POST'])
def delete_note():  
    note = json.loads(request.data) # this function expects a JSON from the INDEX.js file 
    noteId = note['noteId']
    note = Note.query.get(noteId)
    if note:
        if note.user_id == current_user.id:
            db.session.delete(note)
            db.session.commit()

    return jsonify({})


@views.route('/all-expenses', methods=['GET'])
@login_required
def all_expenses():
    # Retrieve all expenses for the current user
    all_expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()

    return render_template("all_expenses.html", user=current_user, all_expenses=all_expenses)

@views.route('/delete-expense-dashboard', methods=['POST'])
@login_required
def delete_expense_dashboard():
    expense_id = request.json.get('expenseId')

    if expense_id:
        expense = Expense.query.get(expense_id)
        if expense and expense.user_id == current_user.id:
            db.session.delete(expense)
            db.session.commit()
            return jsonify({'message': 'Expense deleted successfully'})

    return jsonify({'error': 'Failed to delete expense'})

@views.route('/budget', methods=['GET', 'POST'])
@login_required
def budget():
    if request.method == 'POST':
        monthly_salary = float(request.form.get('monthlySalary'))
        travel_percentage = float(request.form.get('travelPercentage'))
        groceries_percentage = float(request.form.get('groceriesPercentage'))
        utilities_percentage = float(request.form.get('utilitiesPercentage'))
        housing_percentage = float(request.form.get('housingPercentage'))
        entertainment_percentage = float(request.form.get('entertainmentPercentage'))
        # Add more categories as needed

        # Validate that the percentages add up to 100%
        total_percentage = travel_percentage + groceries_percentage + utilities_percentage + housing_percentage + entertainment_percentage  # Add more percentages here

        if total_percentage != 100:
            flash('Percentage amounts must add up to 100%. Please adjust.', category='error')
        else:
            # Save budget data to the database
            user_budget = Budget.query.filter_by(user_id=current_user.id).first()

            if not user_budget:
                user_budget = Budget(user_id=current_user.id)

            user_budget.monthly_salary = monthly_salary
            user_budget.travel_percentage = travel_percentage
            user_budget.groceries_percentage = groceries_percentage
            user_budget.utilities_percentage = utilities_percentage
            user_budget.housing_percentage = housing_percentage
            user_budget.entertainment_percentage = entertainment_percentage
            # Set more budget percentages here

            db.session.add(user_budget)
            db.session.commit()

            flash('Budget set successfully!', category='success')
    return render_template("budget.html", user=current_user)
