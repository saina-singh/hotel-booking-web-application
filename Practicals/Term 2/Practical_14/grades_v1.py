from flask import Flask, render_template
app = Flask(__name__)   #instatntiating flask app

studentsmarks = {1:10, 2:20, 3:30, 4:40, 5:50, 6:60, 7:70, 8:80, 9:90, 10:100}

@app.route('/students/<int:studentid>')   #flask variable
def grades(studentid):            #function associated with the decorator   
    studentid = int(studentid)    
    if studentid in range(1,11):
        marks = int(studentsmarks[studentid])
        grade = 'Resit'
        if marks > 90:
            grade = 'A+'
        elif (marks > 80) and (marks <= 90):
            grade = 'A'
        elif (marks > 70) and (marks <= 80):
            grade = 'B+'
        elif (marks > 60) and (marks <= 70):
            grade = 'B'
        elif (marks > 50) and (marks <= 60):
            grade = 'C+'
        elif (marks > 40) and (marks <= 50):
            grade = 'C'
        elif (marks > 35) and (marks <= 40):
            grade = 'D+'
        else:
            grade = 'Resit'             
        return render_template('gradestemplate.html', studentid=studentid, marks=marks, grade=grade)
    else:
        return render_template('error.html', error="Student Id not found")

#if __name__ == '__main__':   
#   app.run(debug = True)
if __name__ == '__main__':    #you can skip this if running app on terminal window
    for i in range(13000, 18000):
      try:
         app.run(debug = True, port = i)
         break
      except OSError as e:
         print("Port {i} not available".format(i))