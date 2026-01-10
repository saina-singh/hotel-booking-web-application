from flask import Flask, jsonify, json
app = Flask(__name__)

#let's assume CSCT data is in json format
data_csct = {    
    'zaheer' : 'WebDevelopment',
    'david'  : 'C++',
    'Kamran' : 'Front-end Development',
    'Shelan' : 'Machine Learning',
    'Barkha' : 'Databases',
    'students' : {
        '1001' : 'Andy Miller',
        '1002' : 'Amanda Joseph',
        '1003' : 'Bella Thorn',
        '1004' : 'Augusta Shine',
        '1005' : 'James Miller',
        '1006' : 'Mohammed Saleh'
    },
    'activites' : ["Open days", "Applicant days", "STEM", "Projects days"]
}
#creating separate data dictionary for staff
staff = {
    'zaheer' : 'WebDevelopment',
    'david'  : 'C++',
    'Kamran' : 'Front-end Development',
    'Shelan' : 'Machine Learning',
    'Barkha' : 'Databases'
}
#creating separate data dictionary for students
students = {
    '1001' : 'Andy Miller',
    '1002' : 'Amanda Joseph',
    '1003' : 'Bella Thorn',
    '1004' : 'Augusta Shine',
    '1005' : 'James Miller',
    '1006' : 'Mohammed Saleh'
}
#creating separate data list for activities
activities = ["Open days", "Applicant days", "STEM", "Projects days"]

@app.route('/jsonifysimple')     
def index():
    return jsonify(data_csct)   #returns json data

@app.route('/jsonifyall')     
def index_jsonify():
    return jsonify(staff=staff, students=students, activities=activities) 

@app.route('/jsondumpsloads')        #using json loads and dumps
def data():
    data = json.dumps(data_csct)  #converting object to string 
    data = json.loads(data) #converting string to json object
    return(data)

@app.route('/jsondumpsloadsselected')        
def selecteddata():
    data = json.dumps(data_csct)  #converting object to string 
    data = json.loads(data) #converting string to json object
    output = ""    #to send only selected data from json object
    for item in data['students']:
        output = output + item + ' : ' + data['students'][item] + '<br>'            
    return output

@app.route('/jsondumpsloadsselected/<studentid>')        
def selecteddataavailability(studentid):
    data = json.dumps(data_csct)  #converting object to string 
    data = json.loads(data) #converting string to json object
    output = "student not found"    #to send only selected data from json object
    for item in data['students']:
        if studentid == item:
            output = "student found <br>" + item + ' : ' + data['students'][item] + '<br>'            
            break
    return output

if __name__ == '__main__':   
   app.run(debug = True)
if __name__ == '__main__':    #you can skip this if running app on terminal window
    for i in range(13000, 18000):
      try:
         app.run(debug = True, port = i)
         break
      except OSError as e:
         print("Port {i} not available".format(i))    