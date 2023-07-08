from flask import Flask, jsonify, request
from flask_pymongo import PyMongo
import jwt
from werkzeug.security import generate_password_hash, check_password_hash #Make Hash Password
from datetime import timedelta,datetime
from bson import ObjectId
from var_dump import var_dump

app = Flask(__name__)

secret_key = 't3rs3r4gu3m4ulu4p4' #Private Key For JWT

app.config['MONGO_URI'] = 'mongodb://127.0.0.1:27017/todo_list'  #MongoDB URI 

mongo = PyMongo(app)

@app.route("/api/auth/register", methods=['POST'])
def register():

    data = request.form.to_dict() #Convert Data to JSON Format

    if len(data) != 2 :
        return jsonify({'status' : 'Failed', 'message': 'Data Empty!!'})
    elif data['username'] == "" and data['password'] == "":
        return jsonify({'status' : 'Failed', 'message': 'Username and Password Must Be Filled!!'})
    elif data['username'] == "":
        return jsonify({'status' : 'Failed', 'message': 'Username Must Be Filled!!'})
    elif data['password'] == "":
        return jsonify({'status' : 'Failed', 'message': 'Password Must Be Filled!!'})
    elif mongo.db['user'].find_one({'username' : data['username']}): #Find One Match Data Username From User Table
        return jsonify({'status' : 'Failed', 'message' : 'Username Already Exist!!'}), 401
    elif data['username'] and data['password']:    
        mongo.db['user'].insert_one({'username': data['username'], 'password': generate_password_hash(data['password'])}) #Insert Data To User Table

        return jsonify({
                        'status' : 'Success',
                        'username' : data['username'],
                        'password' : data['password'],
                        'message': 'User Registered Successfully!'
        })

@app.route('/api/auth/login', methods=['POST'])
def login():
    
    data = request.form.to_dict()

    if len(data) != 2 :
        return jsonify({'status' : 'Failed', 'message': 'Data Empty!!'})
    elif data['username'] == "" and data['password'] == "":
        return jsonify({'status' : 'Failed', 'message': 'Username and Password Must Be Filled!!'})
    elif data['username'] == "":
        return jsonify({'status' : 'Failed', 'message': 'Username Must Be Filled!!'})
    elif data['password'] == "":
        return jsonify({'status' : 'Failed','message': 'Password Must Be Filled!!'})
    
    user = mongo.db['user'].find_one({'username': data['username']})  #Find One Match Data Username From User Table
    
    if not user or not check_password_hash(user['password'], data['password']):
        return jsonify({'status' : 'Failed', 'message': 'Invalid Credentials!!'}), 401
    
    payload = {'_id': str(user['_id']), 
               'exp': datetime.utcnow() + timedelta(minutes=130)  #Create Expired Access Token
              }
    access_token = jwt.encode(payload, secret_key, algorithm='HS256')
    
    return jsonify({
                    'status' : 'Success',
                    'payload' : payload,
                    'access_token': access_token,
                    'message': 'Login Successfully!!'
    })

@app.route('/api/todo/add', methods=['POST'])  #Endpoint For Add New Todo List
def add_todo_item():
    try:
        data = request.form.to_dict()

        description = data['description']   #Optional Field    

        if len(data) != 3 :
            return jsonify({'status' : 'Failed', 'message': 'Data Empty!!'})
        elif data['title'] == "":
            return jsonify({'status' : 'Failed', 'message': 'Title Must Be Filled!!'})
        elif data['description'] == "": #Optional Field
            description = False
        elif mongo.db['todo'].find_one({'title' : data['title']}): #Find One Match Data Title From Todo Table
            return jsonify({'status' : 'Failed', 'message' : 'Title Already Exist!!'}), 401    

        data_token = jwt.decode(data['token'], secret_key, algorithms=['HS256'], verify=True)

        user_id = data_token['_id']

        todo_id = mongo.db['todo'].insert_one({
            'title': data['title'],
            'description' : description,
            'status': '1',   #1 is Progress 0 is Completed 2 is Pending 
            'user_id': user_id
        })  #Insert Data To Todo Table

        return jsonify({
            'status' : 'Success',
            'title': data['title'],
            'description' : description,
            'status': '1', 
            'message': 'Todo Item Added Successfully!', 
            'id': str(todo_id.inserted_id)
        })
    except jwt.ExpiredSignatureError:
        return jsonify({
            'status' : 'Failed',
            'message': 'Expired token!'
        }), 401   
    except jwt.InvalidTokenError:
        return jsonify({
            'status' : 'Failed',
            'message': 'Invalid token!'
        }), 401

@app.route('/api/todo/list', methods=['POST'])  #Endpoint For Find All Todo List
def get_todo_list():
    try:
        data = request.form.to_dict()
        data_token = jwt.decode(data['token'], secret_key, algorithms=['HS256'], verify=True)
        user_id = data_token['_id']
        todos = mongo.db['todo'].find({'user_id': user_id})   #Find All List Of Data From Todo Table

        if todos.collection.count_documents({}) == 0:
            return jsonify({'status' : 'Success', 'message': 'Nothing Data to Show!!'}), 401   

        result = []

        for todo in todos:
            result.append({
                'id': str(todo['_id']),
                'title': todo['title'],
                'description': todo['description'],
                'status': todo['status'] 
            })
        
        return jsonify({'status' : 'Success', 'data' : result})
    except jwt.ExpiredSignatureError:
        return jsonify({'status' : 'Failed', 'message': 'Expired Token!!'}), 401   
    except jwt.InvalidTokenError:
        return jsonify({'status' : 'Failed', 'message': 'Invalid Token!!'}), 401                       

@app.route('/api/todo/update', methods=['POST'])
def update_todo_item():
     try:
        data = request.form.to_dict()
        data_token = jwt.decode(data['token'], secret_key, algorithms=['HS256'], verify=True)
        user_id = data_token['_id']

        description = data['description']   #Optional Field    

        if len(data) != 5 :
            return jsonify({'status' : 'Failed', 'message': 'Data Empty!!'}), 401
        elif data['title'] == "":
            return jsonify({'status' : 'Failed', 'message': 'Title Must Be Filled!!'}), 401
        elif data['description'] == "": #Optional Field
            description = False
        elif data['status'] == "":
            return jsonify({'status' : 'Failed', 'message': 'Status Must Be Filled!!'}), 401    
        elif not mongo.db['todo'].find_one({'_id': ObjectId(data['todo_id']), 'user_id': user_id}):
            return jsonify({
                'status' : 'failed',
                'message': 'Todo Item Not Found!!', 
                'id' : data['todo_id'],
            }), 404
        elif mongo.db['todo'].find_one({'title' : data['title']}): #Find One Match Data Title From Todo Table
            return jsonify({
                'status' : 'Failed', 
                'message' : 'Title Already Exist!!'
            }), 401    
         
        updated_data = {
            'title': data['title'],     
            'description': description,
            'status': data['status']
        }
         
        mongo.db['todos'].update_one({'_id': ObjectId(data['todo_id'])}, {'$set': updated_data})

        return jsonify({
            'status' : 'success',
            'data' : {
                'id' : data['todo_id'],
                'title' : updated_data['title'],
                'description' : updated_data['description'],
                'status' : updated_data['status']
            },
            'message': 'Todo Item Updated Successfully!'
        })
     except jwt.ExpiredSignatureError:
        return jsonify({'message': 'Expired Token!!'})   
     except jwt.InvalidTokenError:
        return jsonify({'message': 'Invalid Token!!'})        

@app.route('/api/todo/delete', methods=['POST'])
def delete_todo_item():
    try:
        data = request.form.to_dict()
        data_token = jwt.decode(data['token'], secret_key, algorithms=['HS256'], verify=True)
        user_id = data_token['_id']
        
        if len(data) != 2 :
            return jsonify({'status' : 'Failed', 'message': 'Data Empty!!'}), 401
        elif data['todo_id'] == "":
            return jsonify({'status' : 'Failed', 'message': 'Todo ID Must Be Filled!!'}), 401    

        todo = mongo.db['todo'].find_one({'_id': ObjectId(data['todo_id']), 'user_id': user_id})

        if not todo:
            return jsonify({
                'status' : 'failed',
                'message': 'Todo Item Not Found!!', 
                'id' : data['todo_id'],
            }), 404
        
        mongo.db['todo'].delete_one({'_id': ObjectId(data['todo_id'])})
        
        return jsonify({
            'status' : 'failed',
            'data' : {
                'id' : data['todo_id'],
                'title' : todo['title'],
                'description' : todo['description'],
                'status' : todo['status']
            },
            'message': 'Todo Item Deleted Successfully!'
        })
    
    except jwt.ExpiredSignatureError:
        return jsonify({'message': 'Expired Token!!'})   
    except jwt.InvalidTokenError:
        return jsonify({'message': 'Invalid Token!!'})    

if __name__ == '__main__':
    app.run(port=5000, debug=True) 



