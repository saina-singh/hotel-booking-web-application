from flask import Flask
app = Flask(__name__)   #instatntiating flask app

output = """
<html>
  <head>
    
    <title>Web Development - HTML example</title>
       
  </head>
  <body>
    
  <h1>University of the West of England, Bristol</h1>
  
  <ul>
      <li><a href="http://www1.uwe.ac.uk/aboutus/departmentsandservices/facultiesanddepartments">University
            Faculties and Departments</a></li>
      <li><a href="http://www1.uwe.ac.uk/aboutus/learningandteaching">Learning
            and Teaching</a></li>
      <li><a href="http://www1.uwe.ac.uk/research">Research</a></li>
  </ul>
  
  <p>University is using blended learning approaches for 2020-21</p>
  <h2>University Faculties and Departments</h2>
  
  
  <h2>Faculty of Environment and Technology </h2>
  <p>The Faculty of Environment and Technology at UWE, is situated in the
          beautiful city of Bristol. We are a highly successful and very popular
          Faculty of over 6000 students and 450 staff members.
  </p>
  
  
  <h2>Faculty of Business and Law</h2>
  <p>The Faculty of Business and Law comprises Bristol Business School and
          Bristol Law School who provide a range of undergraduate, postgraduate,
          higher research and professional courses covering a wide variety of
          business and law subjects.
  </p>
  
  <h2>Faculty of Health and Applied Sciences</h2>
  <p>The Faculty of Health and Applied Sciences brings together experts
          from Allied Health Professions, Biological, Biomedical and Analytical
          Sciences, Health and Social Science, and Nursing and Midwifery. See
          our department web pages to find out more about our excellent teaching
          and research.
  </p>

  
  
  <p>(c) 2020 UWE. All rights reserved.</p>
  
  </body>
</html>
"""

@app.route('/index')
@app.route('/')         #Decorator
def index():            #function associated with the decorator
   print ('Hello')        
   return output



#if __name__ == '__main__':   
#   app.run(debug = True)
if __name__ == '__main__':    #you can skip this if running app on terminal window
    for i in range(13000, 18000):
      try:
         app.run(debug = True, port = i)
         break
      except OSError as e:
         print("Port {i} not available".format(i))