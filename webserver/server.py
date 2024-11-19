import os
import datetime
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, jsonify
import traceback
import click
import random

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
names = []

# Use the DB credentials you received by e-mail
DB_USER = "cch2201"
DB_PASSWORD = "cch2201"
DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"
DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/w4111"

@app.before_request
def before_request():
    engine = create_engine(DATABASEURI)
    conn = engine.connect()
    conn.execute(text("""SET search_path TO cch2201;"""))
    # Here we create a test table and insert some values in it

    try:
        g.conn = engine.connect()
    except:
        print("uh oh, problem connecting to database")
        traceback.print_exc()
        g.conn = None

@app.teardown_request
def teardown_request(exception):
  try:
    g.conn.close()
  except Exception as e:
    pass

@app.route('/', methods=['GET', 'POST'])
def books():
    data = []
    keys = []
    parameters={}
    query = "select Book.BID, quantity -  (select count(*) from Loan_Record where return is null and Book.bid = Loan_Record.bid) Copy, Book.name Name, author, Category.name Category, Publisher.name Publisher from Book, Book_Category, Category, Book_Publisher, Publisher where Book.bid = Book_Category.bid and Book_Category.cid= Category.cid and Book_Publisher.bid = book.bid and Book_Publisher.pid = Publisher.pid "
    # query = "select Book.BID bid, quantity -  (select count(*) from Loan_Record where return is null and Book.bid = Loan_Record.bid) Copy, Book.name Name, author from Book"
    # query = "select * from book"

    if request.method == 'POST':
        search_by = request.form['search_by']
        print(search_by)
        sort_by = request.form['sort_by']
        sort_order = request.form['order']
        parameters = {
            'search_query': "%"+request.form['search']+"%",
        }

        print(parameters['search_query'])
        query += " and " + search_by + " LIKE  :search_query ORDER BY " + sort_by + " " + sort_order
        print(text(query), parameters)
        cursor = g.conn.execute(text(query), parameters)
    else:
        cursor = g.conn.execute(text(query))

    for i in cursor:
        data.append(list(i))

    cursor = g.conn.execute(text(query),parameters).keys()
    for i in cursor:
        keys.append(i)

    return render_template('index.html', keys=keys, data=data)
@app.route('/borrow', methods=['POST'])
def borrow_book():

    try:
        # Get data from the request
        request_data = request.get_json()
        user_id = str(request_data['UID'])
        book_id = str(request_data['BID'])
        issue = datetime.date.today().strftime("%Y-%m-%d")
        due = (datetime.date.today()+ datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        parameters = {
            'book_id': book_id,
            'issue': issue,
            'due': due,
            'user_id': user_id,

        }

        check = "select quantity -  (select count(*) from Loan_Record where return is null and Book.bid = Loan_Record.bid) count from Book where bid = " + book_id
        check_result = g.conn.execute(text(check)).fetchone()
        if int(check_result[0]) <= 0:
            return jsonify({'success': False})
        # check_query = "select Loan_Record.loanid, uid, bid from User_Loan_Record, Loan_Record where User_Loan_Record.LoanID = Loan_Record.LoanID and Loan_Record.bid = :book_id and uid = :user_id"
        # check_result = g.conn.execute(text(check_query), parameters).fetchone()
        # print(check_result)

        insert_query = """
        INSERT INTO Loan_Record (BID, Issue, Due, Return)
        VALUES (:book_id, :issue, :due, NULL)
        RETURNING LoanID
        """
        # print(text(insert_query), parameters)
        result = g.conn.execute(text(insert_query), parameters)
        g.conn.commit()
        loan_id = str(result.fetchone()[0])
        # print("loan_id:"+loan_id)
        parameters['loan_id'] = loan_id

        insert_user_loan_query = """
        INSERT INTO user_loan_record (UID, LoanID)
        VALUES (:user_id, :loan_id)
        """
        g.conn.execute(text(insert_user_loan_query), parameters)
        g.conn.commit()
        return jsonify({'success': True})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False})
@app.route('/return', methods=['POST'])
def return_book():
    request_data = request.get_json()
    loan_id = request_data['loan_id']
    # check_query = "SELECT * FROM Loan_Record WHERE loanid = :loan_id"
    # check_result = g.conn.execute(text(check_query), {'loan_id': loan_id}).fetchone()
    # print(check_result)
    try:
        current_date = datetime.date.today().strftime("%Y-%m-%d")
        query = """
            UPDATE Loan_Record
            SET Return = :return_date
            WHERE LoanID = :loan_id
        """
        params = {
            'return_date': current_date,
            'loan_id': loan_id  # Make sure loan_id is passed as a parameter
        }
        g.conn.execute(text(query), params)
        g.conn.commit()

        # check_query = "SELECT * FROM Loan_Record WHERE loanid = :loan_id"
        # check_result = g.conn.execute(text(check_query), {'loan_id': loan_id}).fetchone()
        # print(check_result)
        return jsonify({'success': True})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False})
@app.route('/user_loan', methods=['get','post'])
def user_loan():
    data = []
    keys=[]
    # uid = request.args.get('UID')

    query = "select users.uid, users.name, Loan_Record.loanid, Loan_Record.bid, Loan_Record.issue, Loan_Record.due, Loan_Record.return  from users, User_Loan_Record, Loan_Record where users.uid = User_Loan_Record.uid and User_Loan_Record.LoanID = Loan_Record.LoanID and return is NULL"

    if request.method == 'POST':
        uid = request.form['UID']
        if uid:
            query += f" and users.uid = {uid}"
    cursor = g.conn.execute(text(query))
    for i in cursor:
        data.append(list(i))
    cursor = g.conn.execute(text(query)).keys()
    for i in cursor:
        keys.append(i)
    return render_template('user_loan.html', keys=keys, data=data)
@app.route('/study_room', methods=['get','post'])
def study_room():
    data = []
    keys = []
    # uid = request.args.get('UID')

    query = "select lid, room_number,Study_Room.RoomID, uid, date,start_time,end_time from Study_Room, Book_Study_Room where Study_Room.RoomID = Book_Study_Room.RoomID"

    if request.method == 'POST':
        uid = request.form['UID']
        if uid:
            query += f" and users.uid = {uid}"
    cursor = g.conn.execute(text(query))
    for i in cursor:
        data.append(list(i))
    cursor = g.conn.execute(text(query)).keys()
    for i in cursor:
        keys.append(i)
    return render_template('study_room.html', keys=keys, data=data)
@app.route('/book_study', methods=['POST'])
def book_study():
    if request.method == 'POST':
        uid = request.form['UID']
        room_id = request.form['room_id']
        start = request.form['from']
        time_obj = datetime.datetime.strptime(start, "%H:%M")
        new_time_obj = time_obj + datetime.timedelta(hours=1)
        end = new_time_obj.strftime("%H:%M")
        date = request.form['date']
        parameters ={
            'uid':uid,
            'room_id':room_id,
            'start': start,
            'end':end,
            'date': date

        }
        print(uid,room_id,start,end, date)

        check = "select count(*) from Book_Study_Room where RoomID = "+ room_id + " and Start_time = :start and Date =:date"
        check_result = g.conn.execute(text(check),parameters).fetchone()
        print(int(check_result[0]))
        if int(check_result[0]) > 0:
            return jsonify({'Already booked': False})

        insert_query = """
        INSERT INTO Book_Study_Room (UID, RoomID, Date, Start_time, End_time) 
        VALUES (:uid, :room_id, :date, :start, :end)
        RETURNING Booking_ID
        """
        # print(text(insert_query), parameters)
        try: 
            result = g.conn.execute(text(insert_query), parameters)
            g.conn.commit()
            Booking_ID = str(result.fetchone()[0])
            return f"""
            <h1>Booking Successful!</h1>
            <p>Your Booking_ID is: <strong>{Booking_ID}</strong></p>
            <p>Your Booking_ID is from: <strong>{start}</strong> to <strong>{end}</strong> on <strong>{date}</strong> </p>
            <a href="/study_room">Click here to return to the booking page</a>
            """
        except Exception as e:
            print(f"Error: {e}")
            return "There was an error booking the room. Please try again."
        return jsonify({f'success, id:{Booking_ID}': True})
    
    
@app.route('/cancel_study', methods=['POST'])
def cancel_study():
    # Parse the incoming JSON data
    try:
        request_data = request.get_json()
        booking_id = request_data['booking_id']

        # Check if the booking exists
        check_query = "SELECT COUNT(*) FROM Book_Study_Room WHERE Booking_ID = :booking_id"
        check_result = g.conn.execute(text(check_query), {'booking_id': booking_id}).fetchone()

        if check_result[0] == 0:
            # Booking does not exist
            return jsonify({'success': False, 'message': 'Booking ID does not exist'})

        # Perform the delete query
        delete_query = "DELETE FROM Book_Study_Room WHERE Booking_ID = :booking_id"
        g.conn.execute(text(delete_query), {'booking_id': booking_id})
        g.conn.commit()

        return jsonify({'success': True})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'success': False, 'message': 'An error occurred while canceling the booking'})

@app.route('/order', methods=['GET', 'POST'])
def order():
    data = []
    keys = []
    parameters={}
    query = "select sid, orders.oid, bid, rid, lid,price, date,quantity from orders, manage where orders.oid = manage.oid"

    cursor = g.conn.execute(text(query), parameters)
    for i in cursor:
        data.append(list(i))

    cursor = g.conn.execute(text(query),parameters).keys()
    for i in cursor:
        keys.append(i)

    return render_template('order.html', keys=keys, data=data)

@app.route('/make_order', methods=['POST'])
def make_order():
    data = []
    keys = []
    if request.method == 'POST':
        parameters ={
            'sid':request.form['sid'],
            'bid': request.form['bid'],
            'rid': request.form['rid'],
            'lid': request.form['lid'],
            'price': request.form['price'],
            'quantity': request.form['quantity'],
            'date': request.form['date']

        }

        insert_query = """
        INSERT INTO orders (BID, RID, LID, Price, Date, Quantity)
        VALUES (:bid, :rid, :lid, :price, :date, :quantity)
        RETURNING OID
        """
        result = g.conn.execute(text(insert_query), parameters)
        g.conn.commit()
        oid = str(result.fetchone()[0])
        print("oid:"+oid)
        parameters['oid'] = oid

        insert_user_loan_query = """
        INSERT INTO manage (SID, OID)
        VALUES (:sid, :oid)
        """
        g.conn.execute(text(insert_user_loan_query), parameters)
        g.conn.commit()

    return jsonify({f'success': True})

@app.route('/another', methods=['GET', 'POST'])
def another():
    data = []
    keys = []

    if request.method == 'POST':
        # Get data from a form submission
        search_by = request.form['search_by']
    else:
        # Get data from query parameters
        search_by = "Users"

    query = "SELECT * FROM "
    query += search_by

    print(query)

    # run query for data
    cursor = g.conn.execute(text(query))
    for i in cursor:
        data.append(list(i))

    # run query for keys
    cursor = g.conn.execute(text(query)).keys()
    for i in cursor:
        keys.append(i)

    # Pass the data to the template
    return render_template('another.html', name=search_by, keys=keys, data=data)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get data from the form
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        user_type = request.form['user_type']

        if user_type == 'Family':
            family = 1
            single = None
        elif user_type == 'Single':
            family = None
            single = 1

        email_check_query = "SELECT COUNT(*) FROM users WHERE email = :email"
        email_check_result = g.conn.execute(text(email_check_query), {'email': email}).fetchone()
        if email_check_result[0] > 0:
            return """
            <h1>Registration Failed</h1>
            <p>The email address is already registered. Please use a different email.</p>
            <a href="/register">Click here to try again</a>
            <br>
            <a href="/">Click here to return to the homepage</a>
            """

        # Generate a unique user ID
        while True:
            user_id = str(random.randint(0,1000)) # Generate User_ID
            check_query = "SELECT COUNT(*) FROM users WHERE uid = :user_id"
            result = g.conn.execute(text(check_query), {'user_id': user_id}).fetchone()
            if result[0] == 0:  # If no user exists with this ID, break the loop
                break

        # Insert user into the database
        insert_query = """
        INSERT INTO users (uid, name, email, password, family, single)
        VALUES (:user_id, :name, :email, :password, :family, :single)
        """
        parameters = {
            'user_id': user_id,
            'name': name,
            'email': email,
            'password' : password,
            'family' : family,
            'single' : single
        }

        try:
            g.conn.execute(text(insert_query), parameters)
            g.conn.commit()
            return f"""
            <h1>Registration Successful!</h1>
            <p>Your User ID is: <strong>{user_id}</strong></p>
            <a href="/">Click here to return to the homepage</a>
            """
        except Exception as e:
            print(f"Error: {e}")
            return "There was an error registering the user. Please try again."
    else:
        return render_template('register.html')


if __name__ == "__main__":
    @click.command()
    @click.option('--debug', is_flag=True)
    @click.option('--threaded', is_flag=True)
    @click.argument('HOST', default='0.0.0.0')
    @click.argument('PORT', default=8111, type=int)
    def run(debug, threaded, host, port):


        HOST, PORT = host, port
        print("running on %s:%d" % (HOST, PORT))
        app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)
    run()
