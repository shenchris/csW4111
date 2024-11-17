import os

from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask
from flask import Flask, request, render_template, g, redirect, Response
import traceback

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

@app.route('/')
def books():
    # Retrieve search criteria from the form
    search_query = request.args.get('search', '')
    search_by = request.args.get('search_by', 'Name')  # Search by ID, Name, or Author
    sort_by = request.args.get('sort_by', 'BID')  # Sort by Popularity, Quantity, or Name
    sort_order = request.args.get('order', 'asc')  # Sort order (asc or desc)

    # Define the base SQL query
    query = "SELECT * FROM book"

    # Apply search criteria if a search query is provided
    if search_query:
        query += f" WHERE {search_by} LIKE '%{search_query}%'"

    # Apply sorting based on selected criteria
    if sort_by == 'Quantity':
        query += f" ORDER BY Quantity {sort_order}"
    elif sort_by == 'Name':
        query += f" ORDER BY Name {sort_order}"
    # elif sort_by == 'Popularity':
    #     query += f" ORDER BY Popularity {sort_order}"  # Assuming Popularity column exists
    else:
        query += f" ORDER BY BID {sort_order}"

    # Execute the query with parameters if search query exists
    print(query)
    cursor = g.conn.execute(text(query))
    data = []
    for i in cursor:
        data.append(list(i))
    print(data)
    # Pass the book data to the template
    return render_template('index.html', data=data)


@app.route('/another')
def another():
    # Retrieve search criteria from the form
    search_query = request.args.get('search', '')
    search_by = request.args.get('search_by', 'Users')  # Search by ID, Name, or Author


    # Define the base SQL query
    query = "SELECT * FROM "

    if search_by:
        query += search_by

    # Execute the query with parameters if search query exists
    print(query)
    cursor = g.conn.execute(text(query))
    data = []
    for i in cursor:
        data.append(list(i))

    keys = []
    cursor = g.conn.execute(text(query)).keys()
    for i in cursor:
        keys.append(i)
    # Pass the book data to the template
    return render_template('another.html', name=search_by, keys=keys, data=data)


if __name__ == "__main__":
    print(tmpl_dir)
    app.run()
